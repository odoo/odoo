/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formatX2many } from "../formatters";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class ListX2ManyField extends Component {
    static template = "web.ListX2ManyField";
    static props = { ...standardFieldProps };

    get formattedValue() {
        return formatX2many(this.props.value);
    }
}

export const listX2ManyField = {
    component: ListX2ManyField,
    useSubView: false,
};

registry.category("fields").add("list.one2many", listX2ManyField);
registry.category("fields").add("list.many2many", listX2ManyField);
