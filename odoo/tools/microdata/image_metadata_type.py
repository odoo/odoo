from __future__ import annotations

from .core.object_type import ImageObject, Organization, Person, URL


class ImageMetadata(ImageObject):
    __description__ = "An image and its metadata"
    __gsc_required_properties__ = [
        'contentUrl',
        (['creator', 'creditText', 'copyrightNotice', 'license'], 'or')
    ]

    def __init__(self,
                 content_url: URL,
                 name: str | None = None,
                 creator: Organization | Person | None = None,
                 credit_text: str | None = None,
                 copyright_notice: str | None = None,
                 license: URL | str | None = None,
                 acquire_license_page: URL | str | None = None) -> None:
        super().__init__(
            content_url=content_url,
            name=name,
            creator=creator,
            credit_text=credit_text,
            copyright_notice=copyright_notice,
            license=license,
            acquire_license_page=acquire_license_page
        )
