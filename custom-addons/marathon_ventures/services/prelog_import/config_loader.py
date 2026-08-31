# -*- coding: utf-8 -*-
"""Load per-Program Prelog import configuration."""

import json
import re
from pathlib import Path

from odoo.exceptions import UserError


_DEFAULT_CONFIG = "default.json"


def slugify_program_name(name):
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
    return slug or "default"


def load_program_config(program_name):
    base_path = Path(__file__).resolve().parents[2] / "prelog_configs"
    slug = slugify_program_name(program_name)
    candidate_paths = [
        base_path / f"{slug}.json",
        base_path / _DEFAULT_CONFIG,
    ]
    for path in candidate_paths:
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                config = json.load(handle)
            config["_config_path"] = str(path)
            config["_config_slug"] = slug
            return config
    raise UserError(
        "No Prelog import config was found for Program '%s' and no default config exists."
        % (program_name or "Unknown")
    )
