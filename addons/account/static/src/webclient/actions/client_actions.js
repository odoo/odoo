/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Client action to switch the selected company
 * Serves as a way to change the company from a backend call
 */
async function switchCompany(env, action) {
    env.services.company.setCompanies([action.params.company], false);
}

registry.category("actions").add("switch_company", switchCompany);
