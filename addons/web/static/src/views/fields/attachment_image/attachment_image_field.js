/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const { Component } = owl;

export class AttachmentImageField extends Component {}

AttachmentImageField.template = "web.AttachmentImageField";

AttachmentImageField.displayName = _lt("Attachment Image");
AttachmentImageField.supportedTypes = ["many2one"];

registry.category("fields").add("attachment_image", AttachmentImageField);
