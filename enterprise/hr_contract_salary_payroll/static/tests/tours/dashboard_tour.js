/** @odoo-module **/

import { registry } from "@web/core/registry";
import '@hr_payroll/../tests/tours/dashboard_tour';
import { patch } from "@web/core/utils/patch";

patch(registry.category("web_tour.tours").get("payroll_dashboard_ui_tour"), {
    steps() {
        const originalSteps = super.steps();
        const stepIndex = originalSteps.findIndex((step) => step.id === "input_contract_name");
        originalSteps.splice(stepIndex + 1, 0, {
            /**
             * Add some steps upon creating the contract as new fields are added and are required
             * with the hr_contract_salary module.
             */
            content: "Select Details Tab",
            trigger: '.o_notebook ul > li > a:contains(Details)',
            run: 'click',
        }, {
            content: "Set HR Responsible",
            trigger: 'div[name="hr_responsible_id"] div input',
            run: "edit Laurie",
        }, {
            content: "Select HR Reponsible",
            id: "set_hr_responsible",
            trigger: 'div[name=hr_responsible_id] input',
            run: "edit Laurie",
        }, {
            content: "Select HR Reponsible (2)",
            trigger: 'div[name=hr_responsible_id] .dropdown-item:contains(Laurie)',
            run: "click",
        }, {
            content: "Select Signatories Tab",
            trigger: '.o_notebook ul > li > a:contains(Signatories)',
            run: 'click',
        }, {
            content: "Set Contract Template",
            trigger: 'div.o_field_widget.o_field_many2one[name="sign_template_id"] div input',
            run: "edit Employment",
        }, {
            content: "Select Contract Template",
            trigger: '.ui-menu-item a:contains("Employment")',
            run: "click",
        });
        return originalSteps;
    }
});
