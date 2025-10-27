"""Main module for the authentic application."""

import asyncio
import logging
import os

import typer
from rich.console import Console
from rich.panel import Panel

from authentic.oauth_server import build_oauth2_server
from authentic.config.auth import AuthServerSettings, SimpleAuthSettings
from authentic.logger import configure_logger
from uvicorn import Config, Server

# https://dev.to/composiodev/mcp-oauth-21-a-complete-guide-3g91
# https://github.com/22f2000147/oauth-demo/blob/main/simple-auth/mcp_simple_auth/auth_server.py
# https://github.com/rb58853/mcp-oauth/tree/main

console = Console()
app = typer.Typer()

async def start_server(auth_server_settings: AuthServerSettings, auth_settings: SimpleAuthSettings) -> None:
    
    auth_server = build_oauth2_server(auth_settings, auth_server_settings)

    config = Config(app=auth_server, host=auth_server_settings.host, port=auth_server_settings.port)
    
    server = Server(config)
    await server.serve()

@app.command()
def main(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
) -> None:
    auth_server_settings = AuthServerSettings(debug=debug)
    auth_settings = SimpleAuthSettings()

    # Configure logger
    configure_logger(auth_server_settings.log_level)

    # Display welcome message
    welcome_text = f"""🚀 Welcome to {auth_server_settings.name}!
    Python version: {os.sys.version}
    Working directory: {os.getcwd()}
    Server/App Settings: {auth_server_settings}
    Auth Settings: {auth_settings}
    """
    console.print(Panel(welcome_text, title="Authentic", border_style="blue"))

    # Start the server
    asyncio.run(start_server(auth_server_settings, auth_settings))


if __name__ == "__main__":
    app()
