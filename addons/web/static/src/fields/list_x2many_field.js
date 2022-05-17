/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formatX2many } from "./formatters";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class ListX2ManyField extends Component {
    get formattedValue() {
        return formatX2many(this.props.value);
    }
}

ListX2ManyField.useSubView = false;
ListX2ManyField.props = { ...standardFieldProps };
ListX2ManyField.template = "web.ListX2ManyField";

registry.category("fields").add("list.one2many", ListX2ManyField);
registry.category("fields").add("list.many2many", ListX2ManyField);
