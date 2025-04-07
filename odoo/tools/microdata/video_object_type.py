from __future__ import annotations
from .core.object_type import Duration, CreativeWork, MediaObject
from .core.data_type import DateTime, URL, Boolean, Date
from .event_type import Event
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.interaction_counter_type import InteractionCounter
    from .core.action_type import SeekToAction


class PublicationEvent(Event):
    __description__ = """
        A PublicationEvent corresponds indifferently to the event of publication
        for a CreativeWork of any type, e.g. a broadcast event, an on-demand
        event, a book/journal publication via a variety of delivery media.
    """
    __schema_properties__ = Event.__schema_properties__ | {
        "publishedBy": ["Organization", "Person"],
        "publishedOn": "BroadcastService"
    }


class BroadcastEvent(PublicationEvent):
    __description__ = """
        An over the air or online broadcast event.
    """
    __schema_properties__ = PublicationEvent.__schema_properties__ | {
        "broadcastOfEvent": "Event",
        "isLiveBroadcast": "Boolean",
        "subtitleLanguage": ['r', "Language", "Text"],
        "videoFormat": "Text"
    }

    def __init__(self,
                 name: str,
                 start_date: DateTime | Date | str | None,
                 end_date: DateTime | Date | str | None,
                 is_live_broadcast: Boolean = Boolean(True),
                 **kwargs) -> None:
        super().__init__(
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_live_broadcast=is_live_broadcast,
            **kwargs)


class Clip(CreativeWork):
    __description__ = """
        A short TV or radio program or a segment/part of a program.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "actor": ['r', "PerformingGroup", "Person"],
        "clipNumber": ["Integer", "Text"],
        "director": ['r', "Person"],
        "endOffset": ["HyperTocEntry", "Number"],
        "musicBy": ['r', "MusicGroup", "Person"],
        "partOfEpisode": "Episode",
        "partOfSeason": "CreativeWorkSeason",
        "partOfSeries": "CreativeWorkSeries",
        "startOffset": ["HyperTocEntry", "Number"]
    }

    def __init__(self, name: str,
                 start_offset: int,
                 url: URL | str,
                 end_offset: int | None = None,
                 **kwargs) -> None:
        super().__init__(
            name=name,
            start_offset=start_offset,
            url=url,
            end_offset=end_offset,
            **kwargs
        )


class VideoObject(MediaObject):
    __description__ = "A video file"
    __schema_properties__ = MediaObject.__schema_properties__ | {
        "actor": ['r', "PerformingGroup", "Person"],
        "caption": ['r', "MediaObject", "Text"],
        "director": ['r', "Person"],
        "embeddedTextCaption": 'Text',
        "musicBy": ['r', "MusicGroup", "Person"],
        "transcript": "Text",
        "videoFrameSize": "Text",
        "videoQuality": "Text"
    }

    def __init__(self,
                 name: str,
                 thumbnail_url: list[URL | str],
                 upload_date: DateTime | str,
                 content_url: URL | str | None = None,
                 description: str | None = None,
                 duration: Duration | str | None = None,
                 embed_url: URL | None = None,
                 expires: DateTime | None = None,
                 has_part: list[Clip] | None = None,
                 potential_action: SeekToAction | None = None,
                 ineligible_region: list[str] | None = None,
                 interaction_statistic: InteractionCounter | None = None,
                 publication: list[BroadcastEvent] | None = None,
                 regions_allowed: list[str] | None = None,
                 **kwargs) -> None:
        super().__init__(
            name=name,
            thumbnail_url=thumbnail_url,
            upload_date=upload_date,
            content_url=content_url,
            description=description,
            duration=duration,
            embed_url=embed_url,
            expires=expires,
            has_part=has_part,
            potential_action=potential_action,
            ineligible_region=ineligible_region,
            interaction_statistic=interaction_statistic,
            publication=publication,
            regions_allowed=regions_allowed,
            **kwargs
        )
