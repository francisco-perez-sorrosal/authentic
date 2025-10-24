from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    name: str = Field(default="Authentic", description="A simple authentication server")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")
    host: str = Field(default="0.0.0.0", description="Host to run the server on")
    port: int = Field(default=8000, description="Port to run the server on")

    @model_validator(mode="after")
    def override_log_level(self) -> "Settings":
        """Override log_level to DEBUG if debug flag is True."""
        if self.debug:
            self.log_level = "DEBUG"
        return self
