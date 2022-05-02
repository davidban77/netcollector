"""Module that hold Base collector model."""
from pydantic import BaseModel


class BaseResourceModel(BaseModel):
    """Base Data Model for all collector to have."""
    class Config:
        validate_assignment = True
        extra = "ignore"
