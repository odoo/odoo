/**
 * Add custom steps to take products and sales order into account
 */
import { registry } from "@web/core/registry";
import "@industry_fsm/js/tours/industry_fsm_tour";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { markup } from "@odoo/owl";

patch(registry.category("web_tour.tours").get("industry_fsm_tour"), {
    steps() {
        const originalSteps = super.steps();
        const fsmStartStepIndex = originalSteps.findIndex((step) => step.id === "fsm_start");
        originalSteps.splice(
            fsmStartStepIndex + 1,
            0,
            {
                trigger: 'button[name="action_timer_stop"]',
            },
            {
                trigger: 'button[name="action_fsm_view_material"]',
            content: markup(_t('Let\'s <b>track the material</b> you use for your task.')),
                tooltipPosition: 'bottom',
                run: "click",
            },
            {
                trigger: ".o-kanban-button-new",
            content: markup(_t('Let\'s create a new <b>product</b>.')),
                tooltipPosition: 'right',
                run: "click",
            },
            {
                trigger: '.o_field_text textarea',
            content: markup(_t('Choose a <b>name</b> for your product <i>(e.g. Bolts, Screws, Boiler, etc.).</i>')),
                tooltipPosition: 'right',
                run: "edit Test",
            },
            {
                trigger: ".breadcrumb-item.o_back_button",
            content: markup(_t("Use the breadcrumbs to navigate to your <b>list of products</b>.")),
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                trigger: ".o_fsm_product_kanban_view",
            },
            {
                trigger:
                    ".o_kanban_record:first-child button:has(i.fa-shopping-cart), .o_fsm_product_kanban_view .o_kanban_record",
            content: markup(_t('Click on a product to add it to your <b>list of materials</b>. <i>Tip: for large quantities, click on the number to edit it directly.</i>')),
                tooltipPosition: "right",
                run: "click",
            },
            {
                trigger: ".o_fsm_product_kanban_view",
            },
            {
                trigger: ".breadcrumb-item.o_back_button",
            content: markup(_t("Use the breadcrumbs to return to your <b>task</b>.")),
                tooltipPosition: "bottom",
                run: "click",
            }
        );
        const fsmCreateInvoiceStepIndex = originalSteps.findIndex(
            (step) => step.id === "fsm_invoice_create"
        );
        originalSteps.splice(
            fsmCreateInvoiceStepIndex + 1,
            0,
            {
                trigger: ".o_statusbar_buttons > button:contains('Create Invoice')",
            content: markup(_t("<b>Invoice your time and material</b> to your customer.")),
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                trigger: ".modal-dialog.modal-lg",
            },
            {
                trigger: ".modal-footer button[id='create_invoice_open'].btn-primary",
            content: markup(_t("Confirm the creation of your <b>invoice</b>.")),
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                content: _t("Wait for the invoice to show up"),
                trigger: "span:contains('Customer Invoice')",
            }
        );
        const fsmTimerStopStepIndex = originalSteps.findIndex(
            (step) => step.id === "fsm_save_timesheet"
        );
        originalSteps.splice(
            fsmTimerStopStepIndex + 1,
            0,
            {
                trigger: ".o_form_project_tasks",
                id: 'industry_fsm_sale_sign_send_start',
            },
            {
                trigger: 'button[name="action_preview_worksheet"]',
                content: markup(_t('<b>Review and sign</b> the <b>task report</b> with your customer.')),
                tooltipPosition: 'bottom',
                run: "click",
            },
            {
                trigger: ".o_project_portal_sidebar",
            },
            {
                trigger: 'a[data-bs-target="#modalaccept"]',
                content: markup(_t('Invite your customer to <b>validate and sign your task report</b>.')),
                tooltipPosition: 'right',
                id: 'sign_report',
                run: "click",
            },
            {
                trigger: ".o_project_portal_sidebar",
            },
            {
                isActive: ["auto"],
                trigger: 'div[class="container"] h5#time_and_material',
                content: ('"Time and Material" section is rendered'),
                run: "click",
            },
            {
                trigger: ".o_project_portal_sidebar",
            },
            {
                isActive: ["auto"],
                trigger: 'div[class="container"] tbody[class="sale_tbody"]:not(:empty)',
                content: ('At least a product is rendered'),
                run: "click",
            },
            {
                trigger: '.o_web_sign_auto_button',
                content: markup(_t('Save time by automatically generating a <b>signature</b>.')),
                tooltipPosition: 'right',
                run: "click",
            },
            {
                trigger: ".o_project_portal_sidebar",
            },
            {
                trigger: '.modal .o_portal_sign_submit',
                content: markup(_t('Validate the <b>signature</b>.')),
                tooltipPosition: 'left',
                run: "click",
            },
            {
                trigger: ".o_project_portal_sidebar",
            },
            {
                trigger: "body:not(:has(.modal:contains(sign report))) .alert-info a.alert-link:contains(Back to edit mode)",
                content: markup(_t('Go back to your Field Service <b>task</b>.')),
                tooltipPosition: 'right',
                run: "click",
            },
            {
                trigger: ".o_form_project_tasks",
            },
            {
                trigger: 'button[name="action_send_report"]',
                content: markup(_t('<b>Send your task report</b> to your customer.')),
                tooltipPosition: 'bottom',
                run: "click",
            },
            {
                trigger: '.modal .o_input',
                content: markup(_t('<b>Click to edit.')),
                run: 'click',
            },
            {
                isActive: ["body:not(:has(.modal-footer button.o_mail_send))"],
                trigger: 'button[name="document_layout_save"]',
                content: markup(_t('Customize your <b>layout</b>.')),
                tooltipPosition: 'right',
                run: "click",
            },
            {
                trigger: ".o_form_project_tasks",
            },
            {
                trigger: 'button.o_mail_send',
                content: markup(_t('<b>Send your task report</b> to your customer.')),
                tooltipPosition: 'right',
                run: "click",
                id: 'industry_fsm_sale_sign_send_end',
            },
        );
        return originalSteps;
    },
});
