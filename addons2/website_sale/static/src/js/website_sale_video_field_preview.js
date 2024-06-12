/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class FieldVideoPreview extends Component {}
FieldVideoPreview.template = 'website_sale.FieldVideoPreview';

export const fieldVideoPreview = {
    component: FieldVideoPreview,
};

registry.category("fields").add("video_preview", fieldVideoPreview);
