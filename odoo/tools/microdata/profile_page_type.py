from __future__ import annotations
from .core.object_type import Person, Organization, WebPage
from .core.data_type import DateTime, Date


class ProfilePage(WebPage):
    __description__ = """
        Web page type: Profile page.
    """
    __gsc_required_properties__ = [
        'mainEntity'
    ]

    def __init__(self,
                 main_entity: Person | Organization,
                 date_created: DateTime | Date | None = None,
                 date_modified: DateTime | Date | None = None,
                 **kwargs) -> None:
        super().__init(
            main_entity=main_entity,
            date_created=date_created,
            date_modified=date_modified,
            **kwargs
        )
