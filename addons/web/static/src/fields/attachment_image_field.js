/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;

export class AttachmentImageField extends Component {}

AttachmentImageField.template = "web.AttachmentImageField";
AttachmentImageField.supportedTypes = ["many2one"];

registry.category("fields").add("attachment_image", AttachmentImageField);
