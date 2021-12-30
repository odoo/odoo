/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;

export class DomainSelectorFieldInput extends Component {
    parseValue(value) {
        const parser = registry.category("parsers").get(this.props.field.type, (value) => value);
        return parser(value);
    }

    onChange(ev) {
        this.props.update({ value: this.parseValue(ev.target.value) });
    }
}
DomainSelectorFieldInput.template = "web.DomainSelectorFieldInput";
