/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;

const dsf = registry.category("domain_selector/fields");
const dso = registry.category("domain_selector/operator");

export class DomainSelectorSelectionField extends Component {
    onChange(ev) {
        this.props.update({ value: ev.target.value });
    }
}
Object.assign(DomainSelectorSelectionField, {
    template: "web.DomainSelectorSelectionField",

    onDidTypeChange(field) {
        return { value: field.selection[0][0] };
    },
    getOperators() {
        return ["=", "!=", "set", "not set"].map((key) => dso.get(key));
    },
});

dsf.add("selection", DomainSelectorSelectionField);
