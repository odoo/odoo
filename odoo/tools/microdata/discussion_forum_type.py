from __future__ import annotations
from .article_type import SocialMediaPosting
from .core.object_type import Person, Organization, URL, ImageObject, DateTime, Date, CreativeWork
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .video_object_type import VideoObject


class Comment(CreativeWork):
    __description__ = """
        A comment on an item - for example, a comment on a blog post. The
        comment's content is expressed via the text property, and its topic via
        about, properties shared with all CreativeWorks.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "downvoteCount": "Integer",
        "parentItem": ["Comment", "CreativeWork"],
        "sharedContent": ['r', "CreativeWork"],
        "upvoteCount": "Integer"
    }

    def __init__(self,
                 author: Person | Organization | None = None,
                 date_published: DateTime | Date | str | None = None,
                 text: str | None = None,
                 image: ImageObject | URL | str | None = None,
                 video: VideoObject | None = None,
                 **kwargs) -> None:
        super().__init__(author=author,
                         date_published=date_published,
                         text=text,
                         image=image,
                         video=video,
                         **kwargs)


class DiscussionForumPosting(SocialMediaPosting):
    __description__ = """
        A posting to a discussion forum.
    """
    __schema_properties__ = SocialMediaPosting.__schema_properties__ | {
        "sharedContent": ['r', "CreativeWork"]
    }
    __gsc_required_properties__ = [
        'author',
        'author.name',
        'datePublished',
        (['text', 'image', 'video'], 'or')
    ]

    def __init__(self,
                 author: Person | Organization,
                 date_published: DateTime | Date | str,
                 text: str | None = None,
                 image: ImageObject | URL | None = None,
                 video: VideoObject | None = None,
                 **kwargs):
        super().__init__(author=author,
                         date_published=date_published,
                         text=text,
                         image=image,
                         video=video,
                         **kwargs)
