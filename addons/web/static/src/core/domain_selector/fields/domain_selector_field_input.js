/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;
const parsers = registry.category("parsers");

export class DomainSelectorFieldInput extends Component {
    parseValue(value) {
        const parser = parsers.get(this.props.field.type, (value) => value);
        try {
            return parser(value);
        } catch (_) {
            return value;
        }
    }

    onChange(ev) {
        this.props.update({ value: this.parseValue(ev.target.value) });
    }
}
DomainSelectorFieldInput.template = "web.DomainSelectorFieldInput";
