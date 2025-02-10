from __future__ import annotations
from .core.object_type import (
    AlignmentObject, URL, Duration
)
from .core.data_type import DateTime, Date
from .core.action_type import SeekToAction
from .core.interaction_counter_type import InteractionCounter
from .video_object_type import VideoObject
from .course_info_type import LearningResource
from .video_object_type import Clip, BroadcastEvent


class LearningClip(Clip, LearningResource):
    __schema_properties__ = Clip.__schema_properties__ | LearningResource.__schema_properties__
    __type_name__ = ["Clip", "LearningResource"]

    def __init__(self, name: str,
                 start_offset: int,
                 url: URL | str,
                 learning_resource_type: str | None = None,
                 text: str | None = None,
                 end_offset: int | None = None,
                 **kwargs) -> None:
        super().__init__(
            name=name,
            start_offset=start_offset,
            url=url,
            learning_resource_type=learning_resource_type,
            text=text,
            end_offset=end_offset,
            **kwargs
        )


class LearningVideo(VideoObject, LearningResource):
    __schema_properties__ = VideoObject.__schema_properties__ | LearningResource.__schema_properties__
    __type_name__ = ["VideoObject", "LearningResource"]

    def __init__(self,
                 name: str,
                 thumbnail_url: list[URL | str],
                 upload_date: DateTime | Date | str,
                 educational_alignment: AlignmentObject | None = None,
                 educational_level: str | None = None,
                 learning_resource_type: str | None = None,
                 content_url: URL | str | None = None,
                 description: str | None = None,
                 duration: Duration | str | None = None,
                 embed_url: URL | None = None,
                 expires: DateTime | Date | str | None = None,
                 has_part: list[LearningClip] | None = None,
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
            educational_alignment=educational_alignment,
            educational_level=educational_level,
            learning_resource_type=learning_resource_type,
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