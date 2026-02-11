import json
import uuid

from odoo import models

PAGE_PAYLOAD_FIELDS = (
    "name",
    "url",
    "website_id",
    "view_id",
    "is_published",
    "publish_on",
    "website_indexed",
    "is_new_page_template",
    "parent_id",
    "header_visible",
    "footer_visible",
    "breadcrumb_visible",
    "header_overlay",
    "header_color",
    "header_text_color",
    "breadcrumb_overlay",
    "breadcrumb_color",
    "breadcrumb_text_color",
)

CONTROLLER_PAGE_PAYLOAD_FIELDS = (
    "view_id",
    "record_view_id",
    "record_domain",
    "default_layout",
    "name_slugified",
    "is_published",
    "publish_on",
)

VIEW_PAYLOAD_FIELDS = (
    "key",
    "name",
    "type",
    "model",
    "arch_db",
    "inherit_id",
    "mode",
    "priority",
    "website_id",
    "active",
    "track",
    "visibility",
    "visibility_password",
    "website_meta_title",
    "website_meta_description",
    "website_meta_keywords",
    "website_meta_og_img",
    "seo_name",
)

MENU_PAYLOAD_FIELDS = (
    "name",
    "url",
    "page_id",
    "controller_page_id",
    "parent_id",
    "website_id",
    "sequence",
    "new_window",
    "is_mega_menu",
    "mega_menu_content",
    "mega_menu_classes",
)

ATTACHMENT_PAYLOAD_FIELDS = (
    "name",
    "mimetype",
    "checksum",
    "type",
    "url",
    "public",
    "res_model",
    "res_id",
    "website_id",
)

ASSET_PAYLOAD_FIELDS = (
    "name",
    "bundle",
    "directive",
    "path",
    "target",
    "active",
    "sequence",
    "website_id",
    "key",
)


def serialize_record(record, field_names):
    values = {"id": record.id}
    for field_name in field_names:
        value = record[field_name]
        if isinstance(value, models.BaseModel):
            value = value.id
        values[field_name] = value
    return values


def extract_payload_values(payload, field_names, skip=None):
    values = {}
    skip = set(skip or ())
    for field_name in field_names:
        if field_name in skip:
            continue
        values[field_name] = payload.get(field_name)
    return values


def compute_payload_checksum(payload_files):
    checksum_source = json.dumps(payload_files, ensure_ascii=True, sort_keys=True).encode()
    return uuid.uuid5(uuid.NAMESPACE_DNS, checksum_source.decode("ascii")).hex
