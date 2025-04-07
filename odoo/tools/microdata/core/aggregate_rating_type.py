from __future__ import annotations
from .rating_type import Rating


class AggregateRating(Rating):
    """Represents an aggregate rating that extends the base `Rating` class.

    This class is used for scenarios where multiple ratings or reviews are aggregated
    to form a summary rating. It includes additional attributes such as `rating_count`
    and `review_count` to track the number of ratings and reviews that contribute
    to the overall rating.

    Attributes:
        rating_value (float | str): The main rating value, which can be a float or string.
        rating_count (int): The number of individual ratings that contribute to the aggregate score.
        review_count (int): The number of reviews that have been submitted.
        worst_rating (float | str): The lowest possible rating, defaults to `0.0`.
        best_rating (float | str): The highest possible rating, defaults to `5.0`.

    Raises:
        ValueError: If both `rating_count` and `review_count` are `None`.

    """
    __description__ = "The average rating based on multiple ratings or reviews."
    __schema_properties__ = Rating.__schema_properties__ | {
        "itemReviewed": "Thing",
        "ratingCount": "Integer",
        "reviewCount": "Integer"
    }

    def __init__(self,
                 rating_value: float | str,
                 rating_count: int | str | None = None,
                 review_count: int | str | None = None,
                 worst_rating: float | str = 0.0,
                 best_rating: float | str = 5.0,
                 **kwargs
    ) -> None:
        if rating_count is None and review_count is None:
            raise ValueError("At least one of 'rating_count' or 'review_count' must be provided.")
        super().__init__(
            review_count=review_count,
            rating_count=rating_count,
            rating_value=rating_value,
            best_rating=best_rating,
            worst_rating=worst_rating,
            **kwargs
        )
