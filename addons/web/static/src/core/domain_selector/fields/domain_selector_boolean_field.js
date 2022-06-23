/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const { Component } = owl;

const dsf = registry.category("domain_selector/fields");

export class DomainSelectorBooleanField extends Component {
    onChange(ev) {
        this.props.update({
            value: ev.target.value === "1",
        });
    }
}
Object.assign(DomainSelectorBooleanField, {
    template: "web.DomainSelectorBooleanField",

    onDidTypeChange() {
        return { value: true };
    },
    getOperators() {
        return [
            {
                category: "equality",
                label: _lt("is"),
                value: "=",
                onDidChange() {},
                matches({ operator }) {
                    return operator === this.value;
                },
            },
            {
                category: "equality",
                label: _lt("is not"),
                value: "!=",
                onDidChange() {},
                matches({ operator }) {
                    return operator === this.value;
                },
            },
        ];
    },
});

dsf.add("boolean", DomainSelectorBooleanField);
