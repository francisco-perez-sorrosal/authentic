from time import time
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from authentic.config.auth import AuthServerSettings, SimpleAuthSettings
from starlette.applications import Starlette

from mcp.server.auth.routes import cors_middleware, create_auth_routes
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions

from authentic.oauth_provider import SimpleOAuthProvider
from starlette.exceptions import HTTPException

from authentic.logger import logger

def build_oauth2_server(auth_settings: SimpleAuthSettings, auth_server_settings: AuthServerSettings) -> Starlette:
    
    oauth_provider = SimpleOAuthProvider(auth_settings, str(auth_server_settings.auth_url), str(auth_server_settings.server_url))
    
    mcp_auth_settings = AuthSettings(
        issuer_url=auth_server_settings.server_url,
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
        logger.info("Handling login callback")        
        return await oauth_provider.handle_login_callback(request)

    routes.append(Route("/login/callback", endpoint=login_callback_handler, methods=["POST"]))


    # Add consent page route (GET)
    async def consent_page_handler(request: Request) -> Response:
        logger.info("Handling consent page for token: {consent_token}")
        consent_token = request.query_params.get("token")
        if not consent_token:
            raise HTTPException(400, "Missing consent token")
        return await oauth_provider.get_tools_consent_page(consent_token)

    routes.append(Route("/consent", endpoint=consent_page_handler, methods=["GET"]))

    # Add consent callback route (POST)
    async def consent_callback_handler(request: Request) -> Response:
        """Handle consent form submission."""
        return await oauth_provider.handle_tools_consent_callback(request)

    routes.append(Route("/consent/callback", endpoint=consent_callback_handler, methods=["POST"]))

    # Add token introspection endpoint (RFC 7662) for Resource Servers
    async def introspect_handler(request: Request) -> Response:
        """
        Token introspection endpoint for Resource Servers.

        Resource Servers call this endpoint to validate tokens without
        needing direct access to token storage.
        """
        form = await request.form()
        token = form.get("token")
        if not token or not isinstance(token, str):
            return JSONResponse({"active": False}, status_code=400)

        # Look up token in provider
        access_token = await oauth_provider.load_access_token(token)
        if not access_token:
            return JSONResponse({"active": False})

        return JSONResponse(
            {
                "active": True,
                "client_id": access_token.client_id,
                "scope": " ".join(access_token.scopes),
                "exp": access_token.expires_at,
                "iat": int(time()),
                "token_type": "Bearer",
                "aud": access_token.resource,  # RFC 8707 audience claim
            }
        )

    routes.append(
        Route(
            "/introspect",
            endpoint=cors_middleware(introspect_handler, ["POST", "OPTIONS"]),
            methods=["POST", "OPTIONS"],
        )
    )
    
    logger.info("--------------------------------")
    logger.info(f"Routes: \n{'\n'.join([f'{route.path} -> {route.endpoint}' for route in routes])}")
    logger.info("--------------------------------")



    return Starlette(routes=routes)
