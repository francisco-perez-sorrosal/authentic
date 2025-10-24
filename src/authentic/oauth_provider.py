import secrets

from time import time
from typing import Any
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from authentic.config.auth import SimpleAuthSettings
from authentic.logger import logger
from authentic.utils import load_template


class SimpleOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    """
    Simple OAuth provider for demo purposes.

    This provider handles the OAuth flow by:
    1. Providing a simple login form for demo credentials
    2. Showing a consent screen for resource access
    3. Issuing MCP tokens after successful authentication and consent
    4. Maintaining token state for introspection
    """

    def __init__(self, settings: SimpleAuthSettings, auth_callback_url: str, server_url: str):
        self.settings = settings
        self.auth_callback_url = auth_callback_url
        self.server_url = server_url
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.tokens: dict[str, AccessToken] = {}
        self.state_mapping: dict[str, dict[str, str | None]] = {}
        # Store authenticated user information and consent data
        self.user_data: dict[str, dict[str, Any]] = {}
        self.pending_consent: dict[str, dict[str, Any]] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Get OAuth client information."""
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull):
        """Register a new OAuth client."""
        self.clients[client_info.client_id] = client_info

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """Generate an authorization URL for simple login flow."""
        state = params.state or secrets.token_hex(16)

        # Store state mapping for callback
        self.state_mapping[state] = {
            "redirect_uri": str(params.redirect_uri),
            "code_challenge": params.code_challenge,
            "redirect_uri_provided_explicitly": str(params.redirect_uri_provided_explicitly),
            "client_id": client.client_id,
            "resource": params.resource,  # RFC 8707
        }

        # Build simple login URL that points to login page
        auth_url = f"{self.auth_callback_url}?state={state}&client_id={client.client_id}"

        return auth_url

    async def get_login_page(self, state: str) -> HTMLResponse:
        """Generate login page HTML for the given state."""
        if not state:
            raise HTTPException(400, "Missing state parameter")

        try:
            html_content = load_template(
                "login.html",
                state=state,
                callback_url=f"{self.server_url.rstrip('/')}/login/callback"
            )
            logger.info(f"Callback URL: {f"{self.server_url.rstrip('/')}/login/callback"}")
            return HTMLResponse(content=html_content)
        except FileNotFoundError as e:
            logger.error(f"Template error: {e}")
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html><head><title>Login</title></head>
            <body>
                <h2>MCP Login</h2>
                <form action="{self.server_url.rstrip('/')}/login/callback" method="post">
                    <input type="hidden" name="state" value="{state}">
                    <p>Username: <input type="text" name="username" value="fps"></p>
                    <p>Password: <input type="password" name="password" value="fps"></p>
                    <p><button type="submit">Sign In</button></p>
                </form>
            </body></html>
            """)
    
    #########################################################
    # Callback handlers
    #########################################################
    
    async def handle_login_callback(self, request: Request) -> Response:
        """Handle login form submission callback."""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        state = form.get("state")

        logger.info(f"Login callback received: username={username}, password={password}, state={state}")

        if not username or not password or not state:
            raise HTTPException(400, "Missing username, password, or state parameter")

        # Ensure we have strings, not UploadFile objects
        if not isinstance(username, str) or not isinstance(password, str) or not isinstance(state, str):
            raise HTTPException(400, "Invalid parameter types")

        # Validate demo credentials
        if username != self.settings.username or password != self.settings.password:
            raise HTTPException(401, "Invalid credentials")

        state_data = self.state_mapping.get(state)
        if not state_data:
            raise HTTPException(400, "Invalid state parameter")

        # Create consent token and store pending consent data
        consent_token = f"consent_{secrets.token_hex(16)}"
        client = await self.get_client(state_data["client_id"])
        
        self.pending_consent[consent_token] = {
            "username": username,
            "state": state,
            "client_name": client.client_name if client else "Unknown Application",
            "authenticated_at": time.time()
        }

        # Redirect to consent page
        consent_url = f"{self.server_url.rstrip('/')}/consent?token={consent_token}"
        return RedirectResponse(url=consent_url, status_code=302)

    #########################################################
    # Protocol methods
    #########################################################
    
    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str) -> AuthorizationCode | None:
        """Load an authorization code."""
        return self.auth_codes.get(authorization_code)
    
    async def exchange_authorization_code(self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode) -> OAuthToken:
        ...
        
    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        ...
    
    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
        ...
    
    async def load_access_token(self, token: str) -> AccessToken | None:
        ...
    
    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        ...