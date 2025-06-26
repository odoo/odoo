import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

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
