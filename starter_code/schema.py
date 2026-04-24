from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

# ==========================================
# ROLE 1: LEAD DATA ARCHITECT
# ==========================================
# v1 Schema - Designed for easy migration to v2.
# Strategy: Use aliases + migration function to handle field renames.

SCHEMA_VERSION = "v1"


class SourceType(str, Enum):
    PDF = "PDF"
    CSV = "CSV"
    HTML = "HTML"
    VIDEO = "Video"  # forensic agent checks for "Video"
    CODE = "Code"


class QualityFlag(str, Enum):
    CLEAN = "clean"
    MISSING_PRICE = "missing_price"
    NEGATIVE_VALUE = "negative_value"
    DUPLICATE = "duplicate"
    DISCREPANCY = "discrepancy"
    NOISE = "noise"
    UNPARSEABLE = "unparseable"


class UnifiedDocument(BaseModel):
    """Unified schema for all data sources in the Knowledge Base."""

    document_id: str
    content: str
    source_type: SourceType
    author: Optional[str] = "Unknown"
    timestamp: Optional[datetime] = None
    title: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    quality_flags: List[QualityFlag] = Field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    # Flexible dict for source-specific data (price, currency, stock, etc.)
    source_metadata: dict = Field(default_factory=dict)

    @field_validator("document_id")
    @classmethod
    def id_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("document_id cannot be empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()


# ==========================================
# V2 MIGRATION HELPER (prepared for mid-lab incident)
# ==========================================
# When v2 is announced, update the field mapping below and bump SCHEMA_VERSION.
# All processors call migrate_to_latest() so changes propagate automatically.

V2_FIELD_RENAMES: dict = {
    # "old_field": "new_field"  # Fill in when v2 is announced
}


def migrate_to_latest(doc_dict: dict) -> dict:
    """Apply any field renames for schema migration.
    Processors should call this before returning their output.
    """
    for old_key, new_key in V2_FIELD_RENAMES.items():
        if old_key in doc_dict:
            doc_dict[new_key] = doc_dict.pop(old_key)
    doc_dict["schema_version"] = SCHEMA_VERSION
    return doc_dict
