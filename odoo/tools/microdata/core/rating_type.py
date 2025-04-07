from __future__ import annotations
from .object_type import Intangible


class Rating(Intangible):
    __description__ = """
        A rating is an evaluation on a numeric scale, such as 1 to 5 stars.
    """
    __schema_properties__ = Intangible.__schema_properties__ | {
        "author": ["Organization", "Person"],
        "bestRating": ["Number", "Text"],
        "ratingExplanation": ["Text"],
        "ratingValue": ["Number", "Text"],
        "reviewAspect": ["Text"],
        "worstRating": ["Number", "Text"]
    }

    def __init__(self,
                 rating_value: float | str,
                 best_rating: float | str = 5.0,
                 worst_rating: float | str = 0.0, **kwargs) -> None:
        super().__init__(
            rating_value=rating_value,
            best_rating=best_rating,
            worst_rating=worst_rating,
            **kwargs)
