from __future__ import annotations
from .core.object_type import Person, Organization, URL, CreativeWork
from .review_type import Review
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.rating_type import Rating


class Claim(CreativeWork):
    __description__ = """
        A Claim in Schema.org represents a specific, factually-oriented claim
        that could be the itemReviewed in a ClaimReview. The content of a claim
        can be summarized with the text property. Variations on well known
        claims can have their common identity indicated via sameAs links, and
        summarized with a name. Ideally, a Claim description includes enough
        contextual information to minimize the risk of ambiguity or inclarity.
        In practice, many claims are better understood in the context in which
        they appear or the interpretations provided by claim reviews.

        Beyond ClaimReview, the Claim type can be associated with related
        creative works - for example a ScholarlyArticle or Question might be
        about some Claim.

        At this time, Schema.org does not define any types of relationship
        between claims. This is a natural area for future exploration.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "appearance": ['r', "CreativeWork"],
        "claimInterpreter": ['r', "Organization", "Person"],
        "firstAppearance": "CreativeWork"
    }


class ClaimReview(Review):
    __description__ = """
        A fact-checking review of claims made (or reported) in some creative
        work (referenced via itemReviewed).
    """
    __schema_properties__ = Review.__schema_properties__ | {
        "claimReviewed": "Text"
    }
    __gsc_required_properties__ = [
        'claimReviewed',
        'reviewRating',
        'url',
        'reviewRating.alternateName'
    ]

    def __init__(self,
                 claim_reviewed: str | None = None,
                 review_rating: Rating | None = None,
                 url: URL | str | None = None,
                 author: Organization | Person | None = None,
                 item_reviewed: Claim | None = None,
                 **kwargs) -> None:
        super().__init__(author=author,
                         review_rating=review_rating,
                         item_reviewed=item_reviewed,
                         url=url,
                         claim_reviewed=claim_reviewed,
                         **kwargs)
