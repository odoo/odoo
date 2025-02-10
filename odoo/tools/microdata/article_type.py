from __future__ import annotations
from .core.object_type import CreativeWork, Person, Organization, ImageObject, URL
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.data_type import URL, DateTime, Date


class Article(CreativeWork):
    __definition__ = """
        An article, such as a news article or piece of investigative report.
        Newspapers and magazines have articles of many different types and this
        is intended to cover them all.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "articleBody": "Text",
        "articleSelection": "Text",
        "backStory": ["CreativeWork", "Text"],
        "pageEnd": ["Integer", "Text"],
        "pageStart": ["Integer", "Text"],
        "pagination": ["Text"],
        "speakable": ["SpeakableSpecification", "URL"],
        "wordCount": "Integer"
    }

    __gsc_required_properties__ = [
        "author",
        "author.name",
        "author.url",
        "dateModified",
        "datePublished",
        "headline",
        "image"
    ]

    def __init__(self,
                 author: Person | Organization | list[Person | Organization],
                 date_modified: DateTime | Date | None = None,
                 date_published: DateTime | Date | None = None,
                 headline: str | None = None,
                 name: str | None = None,
                 image: ImageObject | URL | list[ImageObject | URL] | None = None,
                 url: URL | None = None,
                 **kwargs) -> None:
        super().__init__(
            author=author,
            name=name,
            date_modified=date_modified,
            date_published=date_published,
            headline=headline,
            image=image,
            url=url,
            **kwargs)


class NewsArticle(Article):
    __definition__ = """
        A NewsArticle is an article whose content reports news, or provides
        background context and supporting materials for understanding the news.
    """
    __schema_properties__ = Article.__schema_properties__ | {
        "dateline": "Text",
        "printColumn": "Text",
        "printEdition": "Text",
        "printPage": "Text",
        "printSection": "Text"
    }


class SocialMediaPosting(Article):
    __definition__ = """
        A post to a social media platform, including blog posts, tweets, Facebook posts, etc.
    """
    __schema_properties__ = Article.__schema_properties__ | {
        "sharedContent": "CreativeWork"
    }


class BlogPosting(SocialMediaPosting):
    __definition__ = """
        A blog post.
    """
