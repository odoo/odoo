from __future__ import annotations
from .object_type import CreativeWork


class Movie(CreativeWork):
    __description__ = """
        A movie.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "actor": ['r', "PerformingGroup", "Person"],
        "countryOfOrigin": ['r', "Country"],
        "director": ['r', "Person"],
        "duration": "Duration",
        "musicBy": ['r', "MusicGroup", "Person"],
        "productionCompany": ['r', "Organization"],
        "subtitleLanguage": ['r', "Language", "Text"],
        "titleEIDR": ['r', "Text", "URL"],
        "trailer": ['r', "VideoObject"]
    }
