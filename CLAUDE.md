# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Authentic is a basic authentication server for MCPs (Model Context Protocol) using OAuth 2.1. The project is built with Starlette/Uvicorn for the web server, Typer for CLI, and uses Pydantic for configuration management.

## Development Environment

This project uses **Pixi** for package management and environment isolation. **Always use `pixi run` commands** to ensure the proper Python environment is active.

### Common Commands

```bash
# Install dependencies
pixi install

# Run the application
pixi run start

# Run all tests
pixi run test

# Run a single test file
pixi run pytest tests/test_main.py

# Run a specific test function
pixi run pytest tests/test_main.py::test_settings_defaults

# Lint code
pixi run lint

# Format code
pixi run format
```

## Architecture

### Entry Points

- `src/authentic/__main__.py` - Module entry point for `python -m authentic`
- `src/authentic/main.py` - Contains the Typer CLI app and main command, also hosts the Uvicorn server

### Configuration System

The project uses Pydantic Settings with multiple configuration classes:

1. **Settings** (`src/authentic/settings.py`) - Main application settings
   - Loads from `.env` file
   - Includes server host/port, debug mode, and log level
   - Debug mode automatically sets log level to DEBUG via model validator

2. **SimpleAuthSettings** (`src/authentic/config/auth.py`) - OAuth credentials
   - Uses `MCP_` prefix for environment variables
   - Contains demo user credentials and OAuth scope

3. **AuthServerSettings** (`src/authentic/config/auth.py`) - Authorization server config
   - Loads from `.auth.env` file
   - Has computed fields for `server_url` and `auth_callback_url`

### Server Architecture

The application runs two conceptual servers:
- Main application server (Uvicorn/Starlette) defined in `main.py`
- Authorization server (Starlette) defined in `auth_server.py`

Currently, the main server starts via `asyncio.run(start_server(settings))` in the Typer command.

### Logging

Uses Loguru with Rich console integration for colorized output. Logger is configured in `src/authentic/logger.py` with custom formatting that includes timestamp, level, and code location.

## Testing

- Uses pytest with configuration in `pyproject.toml`
- Test files are in `tests/` directory
- When running tests, remember to pass `_env_file=None` to Settings to avoid loading from actual .env files during tests
