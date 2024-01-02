/* @odoo-module */

import { Persona } from "@mail/core/common/persona_model";

import { patch } from "@web/core/utils/patch";

Persona.id.push("employeeId!");

patch(Persona.prototype, {
    setup() {
        this.employeeId = undefined;
    },
});
