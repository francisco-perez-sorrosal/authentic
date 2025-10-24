# Authentic

A basic authentication server for my MCPs.

## Setup

1. Install dependencies:
```bash
pixi install
```

2. Copy environment file:
```bash
cp .env.example .env
```

## Usage

Run the application:
```bash
pixi run start
```

Run tests:
```bash
pixi run test
```

Format code:
```bash
pixi run format
```

Lint code:
```bash
pixi run lint
```

## Development

This project uses:
- **Pixi** for package management
- **Ruff** for linting and formatting
- **Pytest** for testing
- **Pydantic** for data validation
- **Typer** for CLI
- **Rich** for beautiful console output
- **Loguru** for logging
