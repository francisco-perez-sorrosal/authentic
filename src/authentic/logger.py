"""Logger configuration for the authentic application."""

import os
from threading import Lock
from typing import Optional

from loguru import logger
from rich.console import Console

console = Console()

# Thread-safe configuration lock
_config_lock = Lock()
_configured = False
_current_log_level: Optional[str] = None


def configure_logger(log_level: str = "INFO") -> None:
    """Configure the logger with the specified log level.
    
    This function is idempotent and thread-safe. It can be called multiple times,
    but will only reconfigure if the log level changes.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    global _configured, _current_log_level
    
    # Normalize log level
    log_level = log_level.upper()
    
    with _config_lock:
        # Skip if already configured with the same level
        if _configured and _current_log_level == log_level:
            return
        
        # Remove default handler
        logger.remove()

        # Add console handler with rich formatting
        logger.add(
            console.print,
            level=log_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )
        
        _configured = True
        _current_log_level = log_level


def get_logger():
    """Get the configured logger instance.
    
    This ensures the logger is configured before returning it.
    If not already configured, it will configure with default settings.
    
    Returns:
        The configured loguru logger instance
    """
    if not _configured:
        # Try to get log level from environment, default to INFO
        log_level = os.getenv("LOG_LEVEL", "INFO")
        configure_logger(log_level)
    
    return logger


# Initialize logger on module import with defaults
_initial_log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logger(_initial_log_level)

# Export the configured logger for easy import
# Other modules can use: from authentic.logger import logger
__all__ = ["logger", "configure_logger", "get_logger"]
