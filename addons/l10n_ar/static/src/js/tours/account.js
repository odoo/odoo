/** @odoo-module **/

    import "account.tour";
    import { registry } from "@web/core/registry";
    let account_tour = registry.category("web_tour.tours").get("account_tour");
    // Remove the step suggesting to change the name as it is done another way (document number)
    account_tour.steps = account_tour.steps.filter(step => step.trigger != "input[name=name]");

    // Configure the AFIP Responsibility
    let partner_step_idx = account_tour.steps.findIndex(step => step.trigger == 'div[name=partner_id] input');
    account_tour.steps.splice(partner_step_idx + 2, 0, {
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        trigger: "div[name=l10n_ar_afip_responsibility_type_id] input",
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        position: "bottom",
        content: "Set the AFIP Responsability",
        run: "text IVA",
    })
    account_tour.steps.splice(partner_step_idx + 3, 0, {
        trigger: ".ui-menu-item > a:contains('IVA').ui-state-active",
        auto: true,
        in_modal: false,
    })
