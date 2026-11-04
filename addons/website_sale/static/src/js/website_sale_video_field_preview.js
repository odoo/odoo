/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class FieldVideoPreview extends Component {
    static template = "website_sale.FieldVideoPreview";
    static props = {...standardFieldProps};
}

export const fieldVideoPreview = {
    component: FieldVideoPreview,
};

registry.category("fields").add("video_preview", fieldVideoPreview);
