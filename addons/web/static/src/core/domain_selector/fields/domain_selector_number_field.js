/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DomainSelectorFieldInput } from "./domain_selector_field_input";

const { Component } = owl;

const dsf = registry.category("domain_selector/fields");
const dso = registry.category("domain_selector/operator");

export class DomainSelectorNumberField extends Component {}
Object.assign(DomainSelectorNumberField, {
    template: "web.DomainSelectorNumberField",
    components: {
        DomainSelectorFieldInput,
    },

    onDidTypeChange() {
        return { value: 0 };
    },
    getOperators() {
        return [
            "=",
            "!=",
            ">",
            "<",
            ">=",
            "<=",
            "ilike",
            "not ilike",
            "set",
            "not set",
        ].map((key) => dso.get(key));
    },
});

dsf.add("integer", DomainSelectorNumberField);
dsf.add("float", DomainSelectorNumberField);
dsf.add("monetary", DomainSelectorNumberField);
