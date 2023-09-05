/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import "@account/js/tours/account";

patch(registry.category("web_tour.tours").get("account_tour"), {
    steps() {
        const originalSteps = super.steps();
        // Remove the step suggesting to change the name as it is done another way (document number)
        const filteredSteps = originalSteps.filter((step) => step.trigger != "input[name=name]");
        const stepIndex = filteredSteps.findIndex((step) => step.trigger == 'div[name=partner_id] input');
        filteredSteps.splice(stepIndex + 2, 0, {
            trigger: "div[name=l10n_ar_afip_responsibility_type_id] input",
            extra_trigger: "[name=move_type] [raw-value=out_invoice]",
            position: "bottom",
            content: "Set the AFIP Responsability",
            run: "text IVA",
        })
        filteredSteps.splice(stepIndex + 3, 0, {
            trigger: ".ui-menu-item > a:contains('IVA').ui-state-active",
            auto: true,
            in_modal: false,
        });
        return filteredSteps;
    }
});
