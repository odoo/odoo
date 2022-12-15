/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DomainSelectorFieldInput } from "./domain_selector_field_input";

import { Component } from "@odoo/owl";

const dso = registry.category("domain_selector/operator");

export class DomainSelectorDefaultField extends Component {}
Object.assign(DomainSelectorDefaultField, {
    template: "web.DomainSelectorDefaultField",
    components: {
        DomainSelectorFieldInput,
    },

    onDidTypeChange() {
        return { value: "" };
    },
    getOperators() {
        return dso.getAll();
    },
});
