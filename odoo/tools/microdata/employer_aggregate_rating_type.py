from __future__ import annotations
from .core.aggregate_rating_type import AggregateRating
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.object_type import Organization


class EmployerAggregateRating(AggregateRating):
    __description__ = """
        An aggregate rating of an Organization related to its role as an
        employer.
    """
    __gsc_required_properties__ = [
        'itemReviewed',
        'ratingValue',
        (['reviewCount', 'ratingCount'], 'or')
    ]

    def __init__(self,
                 item_reviewed: Organization,
                 rating_count: int | str,
                 rating_value: float | str | None = None,
                 review_count: int | str | None = None,
                 **kwargs) -> None:
        super().__init__(
            rating_value=rating_value,
            rating_count=rating_count,
            review_count=review_count,
            item_reviewed=item_reviewed,
            **kwargs)
