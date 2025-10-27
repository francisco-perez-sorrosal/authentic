import secrets

from time import time
from typing import Any
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri    
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from authentic.config.auth import SimpleAuthSettings
from authentic.logger import logger
from authentic.utils import load_template


FIVE_MINUTES = 300
ONE_HOUR = 3600

class SimpleOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    """
    Simple OAuth provider for demo purposes.

    This provider handles the OAuth flow by:
    1. Providing a simple login form for demo credentials
    2. Showing a consent screen for resource access
    3. Issuing MCP tokens after successful authentication and consent
    4. Maintaining token state for introspection
    """

    def __init__(self, settings: SimpleAuthSettings, auth_url: str, server_url: str):
        self.settings = settings
        self.auth_url = auth_url
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
        logger.info(f"Getting client information for client_id: {client_id}")
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
        auth_url = f"{self.auth_url}?state={state}&client_id={client.client_id}"

        return auth_url

    async def get_login_page(self, state: str) -> HTMLResponse:
        """Generate login page HTML for the given state."""
        if not state:
            raise HTTPException(400, "Missing state parameter")

        logger.info(f"Getting login page for state: {state}")
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
            
    async def get_tools_consent_page(self, consent_token: str) -> HTMLResponse:
        """Generate consent page HTML for the given consent token."""
        if not consent_token or consent_token not in self.pending_consent:
            raise HTTPException(400, "Invalid or missing consent token")

        consent_data = self.pending_consent[consent_token]
        
        # Define the tools that will be accessible
        available_tools = [
            {
                "name": "run",
                "description": "Run a progam on the server"
            }
        ]

        try:
            html_content = load_template(
                "consent.html",
                username=consent_data['username'],
                client_name=consent_data['client_name'],
                consent_token=consent_token,
                callback_url=f"{self.server_url.rstrip('/')}/consent/callback",
                tools=available_tools
            )
            return HTMLResponse(content=html_content)
        except FileNotFoundError as e:
            logger.error(f"Template error: {e}")
            # Fallback to simple HTML if template not found
            tools_html = ""
            for tool in available_tools:
                tools_html += f"<div><strong>{tool['name']}</strong><br>{tool['description']}</div><br>"
            
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html><head><title>Consent</title></head>
            <body>
                <h2>Resource Access Consent</h2>
                <p>User: {consent_data['username']}</p>
                <p>Client: {consent_data['client_name']}</p>
                <h3>Tools:</h3>
                {tools_html}
                <form action="{self.server_url.rstrip('/')}/consent/callback" method="post">
                    <input type="hidden" name="consent_token" value="{consent_token}">
                    <input type="hidden" name="action" value="approve">
                    <button type="submit">Approve</button>
                </form>
                <form action="{self.server_url.rstrip('/')}/consent/callback" method="post">
                    <input type="hidden" name="consent_token" value="{consent_token}">
                    <input type="hidden" name="action" value="deny">
                    <button type="submit">Deny</button>
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
            "authenticated_at": time()
        }

        # Redirect to consent page
        consent_url = f"{self.server_url.rstrip('/')}/consent?token={consent_token}"
        return RedirectResponse(url=consent_url, status_code=302)

    async def handle_tools_consent_callback(self, request: Request) -> Response:
        """Handle consent form submission callback."""
        form = await request.form()
        consent_token = form.get("consent_token")
        action = form.get("action")

        if not consent_token or not action:
            raise HTTPException(400, "Missing tools consent token or action")

        if not isinstance(consent_token, str) or not isinstance(action, str):
            raise HTTPException(400, "Invalid parameter types")

        consent_data = self.pending_consent.get(consent_token)
        if not consent_data:
            raise HTTPException(400, "Invalid or expired consent token")

        state = consent_data["state"]
        username = consent_data["username"]

        match action.lower():
            case "deny":
                # Clean up consent data but keep state mapping for potential retry
                del self.pending_consent[consent_token]
                
                # Create retry URL
                state_data = self.state_mapping.get(state)
                retry_url = f"{self.server_url.rstrip('/')}/login?state={state}&client_id={state_data['client_id']}" if state_data else "#"
                logger.debug(f"Retry URL: {retry_url}")
                try:
                    html_content = load_template("denied.html", retry_url=retry_url)
                    return HTMLResponse(content=html_content, status_code=403)
                except FileNotFoundError as e:
                    logger.error(f"Template error: {e}")
                    # Fallback to simple HTML
                    return HTMLResponse(content=f"""
                    <!DOCTYPE html>
                    <html><head><title>Access Denied</title></head>
                    <body>
                        <h2>Access Denied</h2>
                        <p>You have denied access to the requested resources.</p>
                        <p><a href="{retry_url}">Try Again</a></p>
                    </body></html>
                    """, status_code=403)

            case "approve":
                # Clean up consent data
                del self.pending_consent[consent_token]                
                # Continue with authorization code flow
                redirect_uri = await self.handle_simple_callback(username, "", state, skip_auth=True)
                return RedirectResponse(url=redirect_uri, status_code=302)
            case _:
                raise HTTPException(400, "Invalid action")

    async def handle_simple_callback(self, username: str, password: str, state: str, skip_auth: bool = False) -> str:
        """Handle simple authentication callback and return redirect URI."""
        state_data = self.state_mapping.get(state)
        if not state_data:
            raise HTTPException(400, "Invalid state parameter")

        logger.debug(f"State data: {state_data}")
        redirect_uri = state_data["redirect_uri"]
        code_challenge = state_data["code_challenge"]
        redirect_uri_provided_explicitly = state_data["redirect_uri_provided_explicitly"] == "True"
        client_id = state_data["client_id"]
        resource = state_data.get("resource")  # RFC 8707

        # These are required values from our own state mapping
        assert redirect_uri is not None
        assert code_challenge is not None
        assert client_id is not None

        # Validate credentials (skip if already authenticated via consent flow)
        if not skip_auth and (username != self.settings.username or password != self.settings.password):
            raise HTTPException(401, "Invalid credentials")

        # Create MCP authorization code
        new_code = f"mcp_{secrets.token_hex(16)}"
        auth_code = AuthorizationCode(
            code=new_code,
            client_id=client_id,
            redirect_uri=AnyHttpUrl(redirect_uri),
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            expires_at=time() + FIVE_MINUTES,
            scopes=[self.settings.mcp_scope],
            code_challenge=code_challenge,
            resource=resource,  # RFC 8707
        )
        self.auth_codes[new_code] = auth_code

        # Store user data
        self.user_data[username] = {
            "username": username,
            "user_id": f"user_{secrets.token_hex(8)}",
            "authenticated_at": time(),
        }

        # Only delete state mapping after successful completion
        del self.state_mapping[state]
        return construct_redirect_uri(redirect_uri, code=new_code, state=state)


    #########################################################
    # Protocol methods
    #########################################################
    
    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str) -> AuthorizationCode | None:
        """Load an authorization code."""
        return self.auth_codes.get(authorization_code)
    
    async def exchange_authorization_code(self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode) -> OAuthToken:
        """Exchange authorization code for tokens."""
        if authorization_code.code not in self.auth_codes:
            raise ValueError("Invalid authorization code")

        # Generate MCP access token
        mcp_token = f"mcp_{secrets.token_hex(32)}"

        # Store MCP token
        self.tokens[mcp_token] = AccessToken(
            token=mcp_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time()) + ONE_HOUR,
            resource=authorization_code.resource,  # RFC 8707
        )

        # Store user data mapping for this token
        self.user_data[mcp_token] = {
            "username": self.settings.username,
            "user_id": f"user_{secrets.token_hex(8)}",
            "authenticated_at": time(),
        }
        # Delete authorization code
        del self.auth_codes[authorization_code.code]

        return OAuthToken(
            access_token=mcp_token,
            token_type="Bearer",
            expires_in=ONE_HOUR,
            scope=" ".join(authorization_code.scopes),
        )
        
    async def load_access_token(self, token: str) -> AccessToken | None:
        """Load and validate an access token."""
        access_token = self.tokens.get(token)
        if not access_token:
            return None

        # Check if expired
        if access_token.expires_at and access_token.expires_at < time():
            del self.tokens[token]
            logger.debug(f"Access token expired: {token}")
            return None

        logger.debug(f"Loaded access token: {token}")
        return access_token
    
    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        logger.warning("Refresh tokens not supported")
        return None
    
    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
        """Exchange refresh token"""
        logger.warning("Refresh tokens not supported")
        raise NotImplementedError("Refresh tokens not supported")
    
    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        """Revoke a token."""
        if isinstance(token, AccessToken) and token.token in self.tokens:
            del self.tokens[token.token]
            logger.debug(f"Revoked access token: {token.token}")
