from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from authentic.config.auth import AuthServerSettings, SimpleAuthSettings
from starlette.applications import Starlette

from mcp.server.auth.routes import cors_middleware, create_auth_routes
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions

from authentic.oauth_provider import SimpleOAuthProvider
from starlette.exceptions import HTTPException

def build_oauth2_server(auth_settings: SimpleAuthSettings, server_settings: AuthServerSettings) -> Starlette:
    
    oauth_provider = SimpleOAuthProvider(auth_settings, server_settings.auth_callback_path, str(server_settings.server_url))
    
    mcp_auth_settings = AuthSettings(
        issuer_url=server_settings.server_url,
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=[auth_settings.mcp_scope],
            default_scopes=[auth_settings.mcp_scope],
        ),
        required_scopes=[auth_settings.mcp_scope],
        resource_server_url=None
    )
    
    routes = create_auth_routes(oauth_provider,
        issuer_url=mcp_auth_settings.issuer_url,
        service_documentation_url=mcp_auth_settings.service_documentation_url,
        client_registration_options=mcp_auth_settings.client_registration_options,
        revocation_options=mcp_auth_settings.revocation_options,
    )

    # Login page handler (GET)
    async def login_page_handler(request: Request) -> Response:
        """Show login form."""
        state = request.query_params.get("state")
        if not state:
            raise HTTPException(400, "Missing state parameter")  # pyright: ignore[reportUndefinedVariable]
        return await oauth_provider.get_login_page(state)

    routes.append(Route("/login", endpoint=login_page_handler, methods=["GET"]))

    # Add login callback route (POST)
    async def login_callback_handler(request: Request) -> Response:
        """Handle simple authentication callback."""
        return await oauth_provider.handle_login_callback(request)

    routes.append(Route("/login/callback", endpoint=login_callback_handler, methods=["POST"]))

    return Starlette(routes=routes)
