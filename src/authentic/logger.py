"""Logger configuration for the authentic application."""

from loguru import logger
from rich.console import Console

console = Console()


def configure_logger(log_level: str) -> None:
    """Configure the logger with the specified log level.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove default handler
    logger.remove()

    # Add console handler with rich formatting
    logger.add(
        console.print,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
