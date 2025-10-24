"""Tests for the main module."""

import pytest
from authentic.settings import Settings


def test_settings_defaults():
    """Test Settings with default values."""
    config = Settings(_env_file=None)
    assert config.name == "Authentic"
    assert config.debug is False
    assert config.log_level == "INFO"
    assert config.host == "0.0.0.0"
    assert config.port == 8000


def test_settings_custom_values():
    """Test Settings with custom values."""
    config = Settings(name="TestApp", debug=True, log_level="DEBUG", host="127.0.0.1", port=3000, _env_file=None)
    assert config.name == "TestApp"
    assert config.debug is True
    assert config.log_level == "DEBUG"
    assert config.host == "127.0.0.1"
    assert config.port == 3000


def test_settings_string_representation():
    """Test Settings string representation."""
    config = Settings(name="TestApp", debug=True, log_level="DEBUG", _env_file=None)
    expected = "name='TestApp' debug=True log_level='DEBUG' host='0.0.0.0' port=8000"
    assert str(config) == expected


def test_settings_debug_override():
    """Test that debug=True overrides log_level to DEBUG."""
    config = Settings(debug=True, log_level="INFO", _env_file=None)
    assert config.debug is True
    assert config.log_level == "DEBUG"
