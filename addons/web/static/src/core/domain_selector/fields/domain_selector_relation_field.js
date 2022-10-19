/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DomainSelectorFieldInput } from "./domain_selector_field_input";

import { Component } from "@odoo/owl";

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

registry
    .category("domain_selector/fields")
    .add("one2many", DomainSelectorRelationField)
    .add("many2one", DomainSelectorRelationField)
    .add("many2many", DomainSelectorRelationField);
