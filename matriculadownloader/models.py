from __future__ import annotations

import os
from dataclasses import asdict, dataclass


@dataclass
class BookEntry:
    url: str
    outdir: str
    pages: str = ""
    status: str = "⏳"

    @classmethod
    def from_dict(cls, data: dict) -> "BookEntry":
        return cls(
            url=str(data.get("url", "")).strip(),
            outdir=str(data.get("outdir", "")).strip() or os.getcwd(),
            pages=str(data.get("pages", "")).strip(),
            status=str(data.get("status", "⏳")).strip() or "⏳",
        )

    def to_dict(self) -> dict:
        return asdict(self)
