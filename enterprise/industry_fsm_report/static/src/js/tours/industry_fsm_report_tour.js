/** @odoo-module **/

/**
 * Adapt the step that is specific to the work details when the `worksheet` module is not installed.
 */

import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { waitUntil } from "@odoo/hoot-dom";

import "@industry_fsm/js/tours/industry_fsm_tour";

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
            trigger: 'button[name="action_fsm_worksheet"]',
            content: markup(_t('Open your <b>worksheet</b> in order to fill it in with the details of your intervention.')),
            tooltipPosition: 'bottom',
                run: "click",
            },
            {
                isActive: ["body:has(.modal .btn-secondary)"],
                trigger: 'button[name="action_generate_new_template"]',
                run:"click",
            },
            {
                trigger: '.o_control_panel:not(:has(button[name="action_fsm_worksheet"]))',
            },
            {
            trigger: '.o_form_sheet div[name] input, .o_form_sheet .note-editable',
            content: markup(_t('Fill in your <b>worksheet</b> with the details of your intervention.')),
            run: "edit My intervention details",
            tooltipPosition: 'bottom',
            },
            {
                isActive: ["auto"],
                trigger: ".o_form_button_save",
                run: "click",
            },
            {
            trigger: ".breadcrumb-item.o_back_button:nth-of-type(2)",
            content: markup(_t("Use the breadcrumbs to return to your <b>task</b>.")),
            tooltipPosition: "bottom",
            run: "click",
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
            },
            {
            trigger: 'button[name="action_preview_worksheet"]',
            content: markup(_t('<b>Review and sign</b> the <b>task report</b> with your customer.')),
            tooltipPosition: 'bottom',
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: ".o_project_portal_sidebar",
            },
            {
                trigger: "a[data-bs-target='#modalaccept']:contains(sign report)",
            content: markup(_t('Invite your customer to <b>validate and sign your task report</b>.')),
            tooltipPosition: 'right',
            id: 'sign_report',
                run: "click",
            },
            {
                trigger: "div[name=worksheet_map] h5#task_worksheet",
                content: '"Worksheet" section is rendered',
            },
            {
                trigger: "div[name=worksheet_map] div[class*=row] div:not(:empty)",
                content: "At least a field is rendered",
            },
            {
                trigger: ".modal .o_web_sign_auto_button:contains(auto)",
            content: markup(_t('Save time by automatically generating a <b>signature</b>.')),
            tooltipPosition: 'right',
                run: "click",
            },
            {
                trigger: ".modal canvas.o_web_sign_signature",
                async run(helpers) {
                    await waitUntil(() => {
                        const canvas = helpers.anchor;
                        const context = canvas.getContext("2d");
                        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
                        const pixels = new Uint32Array(imageData.data.buffer);
                        return pixels.some((pixel) => pixel !== 0);
                    });
                },
            },
            {
                trigger:".modal .o_portal_sign_submit",
                content: markup(_t('Validate the <b>signature</b>.')),
                tooltipPosition: 'left',
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: "body:not(:has(a[data-bs-target='#modalaccept']:contains(sign report))",
            },
            {
                trigger: "body:not(:has(.modal:contains(sign report)))",
            },
            {
                trigger: "body:not(:has(.modal:contains(sign report))) .alert-info a.alert-link:contains(Back to edit mode)",
                content: markup(_t('Go back to your Field Service <b>task</b>.')),
                tooltipPosition: 'right',
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: 'button[name="action_send_report"]:enabled',
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
                trigger: 'button[name="document_layout_save"]:enabled',
            content: markup(_t('Customize your <b>layout</b>.')),
            tooltipPosition: 'right',
                run: "click",
            },
            {
                trigger: ".o_form_project_tasks",
            },
            {
                trigger: 'button.o_mail_send:enabled',
            content: markup(_t('<b>Send your task report</b> to your customer.')),
            tooltipPosition: 'right',
                run: "click",
            }
        );
        return originalSteps;
    },
});
