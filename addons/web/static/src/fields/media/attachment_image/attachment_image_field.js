// @ts-check

/** @module @web/fields/media/attachment_image/attachment_image_field - Read-only image display field for Many2one attachment references */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class AttachmentImageField extends Component {
    static template = "web.AttachmentImageField";
    static props = { ...standardFieldProps };
}

export const attachmentImageField = {
    component: AttachmentImageField,
    displayName: _t("Attachment Image"),
    supportedTypes: ["many2one"],
};

registry.category("fields").add("attachment_image", attachmentImageField);
