from __future__ import annotations
from .core.object_type import Thing, CreativeWork, Person, Organization
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.rating_type import Rating
    from .core.data_type import Date, DateTime


class Review(CreativeWork):
    __description__ = """
        A review of an item - for example, of a restaurant, movie, or store.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "associatedClaimReview": "Review",
        "associatedMediaReview": "Review",
        "associatedReview": "Review",
        "itemReviewed": "Thing",
        "negativeNotes": ['r', "ItemList", "ListItem", "Text", "WebContent"],
        "positiveNotes": ['r', "ItemList", "ListItem", "Text", "WebContent"],
        "reviewAspect": "Text",
        "reviewBody": "Text",
        "reviewRating": "Rating"
    }

    def __init__(self,
                 author: Person | Organization,
                 review_rating: Rating,
                 item_reviewed: Thing | None = None,
                 date_published: DateTime | Date | str | None = None,
                 **kwargs) -> None:
        super().__init__(
            author=author,
            review_rating=review_rating,
            item_reviewed=item_reviewed,
            date_published=date_published,
            **kwargs
        )
