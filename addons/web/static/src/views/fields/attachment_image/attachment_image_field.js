/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { Component } from "@odoo/owl";

export class AttachmentImageField extends Component {
    static template = "web.AttachmentImageField";
}

export const attachmentImageField = {
    component: AttachmentImageField,
    displayName: _t("Attachment Image"),
    supportedTypes: ["many2one"],
};

registry.category("fields").add("attachment_image", attachmentImageField);
