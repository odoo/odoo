/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DomainSelectorFieldInput } from "./domain_selector_field_input";

const { Component } = owl;

const dsf = registry.category("domain_selector/fields");
const dso = registry.category("domain_selector/operator");

export class DomainSelectorRelationField extends Component {}
Object.assign(DomainSelectorRelationField, {
    template: "web.DomainSelectorRelationField",
    components: {
        DomainSelectorFieldInput,
    },

    onDidTypeChange() {
        return { value: "0" };
    },
    getOperators() {
        return ["=", "!=", "ilike", "not ilike", "set", "not set"].map((key) => dso.get(key));
    },
});

dsf.add("one2many", DomainSelectorRelationField);
dsf.add("many2one", DomainSelectorRelationField);
dsf.add("many2many", DomainSelectorRelationField);
