from pydantic import AnyHttpUrl, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SimpleAuthSettings(BaseSettings):
    """Simple OAuth settings for basic authentication purposes."""

    # Basic authentication credentials
    username: str = "fps"
    password: str = "fps"

    # MCP OAuth scope
    mcp_scope: str = "user"


class AuthServerSettings(BaseSettings):
    """Settings for the Authorization Server."""

    model_config = SettingsConfigDict(env_file=".auth.env")

    name: str = Field(default="Authentic", description="A simple authentication server")

    # Logging settings
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")

    # Server settings
    host: str = Field(default="0.0.0.0", description="Host to run the server on")
    port: int = Field(default=9000, description="Port to run the server on")

    # Auth server settings
    auth_host: str = Field(default="0.0.0.0", description="Host to run the auth server on")
    auth_port: int = Field(default=9000, description="Port to run the auth server on")
    auth_path: str = Field(default="/login")

    @computed_field
    @property
    def auth_server_base_url(self) -> AnyHttpUrl:
        """Computed server URL based on host and port."""
        if self.auth_host == "localhost":
            return AnyHttpUrl(f"http://{self.auth_host}:{self.auth_port}")
        else:
            return AnyHttpUrl(f"https://{self.auth_host}:{self.auth_port}")

    @computed_field
    @property
    def auth_url(self) -> AnyHttpUrl:
        """Computed auth URL based on server URL and auth path."""
        # Ensure proper URL joining without double slashes
        base_url = str(self.auth_server_base_url).rstrip("/")
        auth_path = self.auth_path.lstrip("/")
        return AnyHttpUrl(f"{base_url}/{auth_path}")

    @model_validator(mode="after")
    def override_log_level(self) -> "AuthServerSettings":
        """Override log_level to DEBUG if debug flag is True."""
        if self.debug:
            self.log_level = "DEBUG"
        return self
