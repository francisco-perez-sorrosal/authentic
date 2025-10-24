from pydantic import AnyHttpUrl, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SimpleAuthSettings(BaseSettings):
    """Simple OAuth settings for basic authentication purposes."""

    model_config = SettingsConfigDict(env_prefix="MCP_")

    # Basic authentication credentials
    username: str = "fps"
    password: str = "fps"

    # MCP OAuth scope
    mcp_scope: str = "user"


class AuthServerSettings(BaseSettings):
    """Settings for the Authorization Server."""

    model_config = SettingsConfigDict(env_file=".auth.env")

    # Server settings
    host: str = "localhost"
    port: int = 9000
    auth_callback_path: str = Field(default="/login/callback")

    @computed_field
    @property
    def server_url(self) -> AnyHttpUrl:
        """Computed server URL based on host and port."""
        return AnyHttpUrl(f"http://{self.host}:{self.port}")

    @computed_field
    @property
    def auth_callback_url(self) -> AnyHttpUrl:
        """Computed callback URL based on server URL and callback path."""
        # Ensure proper URL joining without double slashes
        base_url = str(self.server_url).rstrip("/")
        callback_path = self.auth_callback_path.lstrip("/")
        return AnyHttpUrl(f"{base_url}/{callback_path}")
