/** @odoo-module */
/**
 * Add custom steps to take products and sales order into account
 */
import { registry } from "@web/core/registry";
import '@industry_fsm/js/tours/industry_fsm_tour';
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { markup } from "@odoo/owl";

patch(registry.category("web_tour.tours").get("industry_fsm_tour"), {
    steps() {
        const originalSteps = super.steps();
        const fsmStartStepIndex = originalSteps.findIndex((step) => step.id === "fsm_start");
        originalSteps.splice(fsmStartStepIndex + 1, 0, {
            trigger: 'button[name="action_fsm_view_material"]',
            extra_trigger: 'button[name="action_timer_stop"]',
            content: markup(_t('Let\'s <b>track the material</b> you use for your task.')),
            position: 'bottom',
        }, {
            trigger: ".o-kanban-button-new",
            content: markup(_t('Let\'s create a new <b>product</b>.')),
            position: 'right',
        }, {
            trigger: '.o_field_text textarea',
            content: markup(_t('Choose a <b>name</b> for your product <i>(e.g. Bolts, Screws, Boiler, etc.).</i>')),
            position: 'right',
        }, {
            trigger: ".breadcrumb-item.o_back_button",
            content: markup(_t("Use the breadcrumbs to navigate to your <b>list of products</b>.")),
            position: "bottom",
        }, {
            trigger: '.o_kanban_record:first-child button:has(i.fa-shopping-cart)',
            alt_trigger: ".o_fsm_product_kanban_view .o_kanban_record",
            extra_trigger: '.o_fsm_product_kanban_view',
            content: markup(_t('Click on a product to add it to your <b>list of materials</b>. <i>Tip: for large quantities, click on the number to edit it directly.</i>')),
            position: 'right',
        }, {
            trigger: ".breadcrumb-item.o_back_button",
            extra_trigger: '.o_fsm_product_kanban_view',
            content: markup(_t("Use the breadcrumbs to return to your <b>task</b>.")),
            position: "bottom"
        });
        const fsmCreateInvoiceStepIndex = originalSteps.findIndex((step) => step.id === "fsm_invoice_create");
        originalSteps.splice(fsmCreateInvoiceStepIndex + 1, 0, {
            trigger: ".o_statusbar_buttons > button:contains('Create Invoice')",
            content: markup(_t("<b>Invoice your time and material</b> to your customer.")),
            position: "bottom"
        }, {
            trigger: ".modal-footer button[id='create_invoice_open'].btn-primary",
            extra_trigger: ".modal-dialog.modal-lg",
            content: markup(_t("Confirm the creation of your <b>invoice</b>.")),
            position: "bottom"
        }, {
            content: _t("Wait for the invoice to show up"),
            trigger: "span:contains('Customer Invoice')",
            run() {},
            auto: true,
        });
        return originalSteps;
    }
});
