/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component }  = owl;

export class FieldVideoPreview extends Component {}
FieldVideoPreview.template = 'website_sale.FieldVideoPreview';

registry.category("fields").add("video_preview", FieldVideoPreview);
