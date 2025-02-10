from __future__ import annotations
from .object_type import CreativeWork


class LearningResource(CreativeWork):
    __description__ = "The LearningResource type can be used to indicate CreativeWorks (whether physical or digital) that have a particular and explicit orientation towards learning, education, skill acquisition, and other educational purposes."
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "assesses": ['r', "DefinedTerm", "Text"],
        "competencyRequired": ['r', "DefinedTerm", "Text", "URL"],
        "educationalAlignment": ['r', "AlignmentObject"],
        "educationLevel": ["DefinedTerm", "Text", "URL"],
        "educationalUse": ['r', "DefinedTerm", "Text"],
        "learningResourceType": ['r', "DefinedTerm", "Text"],
        "teaches": ['r', "DefinedTerm", "Text"]
    }
