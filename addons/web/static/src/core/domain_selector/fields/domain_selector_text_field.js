/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DomainSelectorFieldInput } from "./domain_selector_field_input";
import { DomainSelectorFieldInputWithTags } from "./domain_selector_field_input_with_tags";

import { Component } from "@odoo/owl";

const dsf = registry.category("domain_selector/fields");
const dso = registry.category("domain_selector/operator");

export class DomainSelectorTextField extends Component {}
Object.assign(DomainSelectorTextField, {
    template: "web.DomainSelectorTextField",
    components: {
        DomainSelectorFieldInput,
        DomainSelectorFieldInputWithTags,
    },

    onDidTypeChange() {
        return { value: "" };
    },
    getOperators() {
        return ["=", "!=", "ilike", "not ilike", "set", "not set", "in", "not in"].map((key) =>
            dso.get(key)
        );
    },
});

dsf.add("char", DomainSelectorTextField);
dsf.add("html", DomainSelectorTextField);
dsf.add("text", DomainSelectorTextField);
