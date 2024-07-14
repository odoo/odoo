/** @odoo-module **/

/**
 * Adapt the step that is specific to the work details when the `worksheet` module is not installed.
 */

import { markup } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import '@industry_fsm/js/tours/industry_fsm_tour';

patch(registry.category("web_tour.tours").get("industry_fsm_tour"), {
    steps() {
        const originalSteps = super.steps();
        const fsmStartStepIndex = originalSteps.findIndex((step) => step.id === "fsm_start");
        originalSteps.splice(fsmStartStepIndex + 1, 0, {
            trigger: 'button[name="action_fsm_worksheet"]',
            extra_trigger: 'button[name="action_timer_stop"]',
            content: markup(_t('Open your <b>worksheet</b> in order to fill it in with the details of your intervention.')),
            position: 'bottom',
        }, {
            trigger: '.o_form_sheet div[name]',
            extra_trigger: '.o_control_panel:not(:has(button[name="action_fsm_worksheet"]))',
            content: markup(_t('Fill in your <b>worksheet</b> with the details of your intervention.')),
            run: function (actions) {
                //Manage the text on both htmlElement and others fields as this step is dependent on
                // the worksheet template that is set.
                const htmlFieldSelector = '.note-editable.odoo-editor-editable p';
                const inputFieldSelector = 'input';
                const textTriggerElement = this.$anchor.find(htmlFieldSelector).get(0)
                                            || this.$anchor.find(inputFieldSelector).get(0)
                                            || this.$anchor.get(0);
                actions.text('My intervention details', textTriggerElement);
            },
            position: 'bottom',
        }, {
            trigger: ".o_form_button_save",
            auto: true,
        }, {
            trigger: ".breadcrumb-item.o_back_button:nth-of-type(2)",
            content: markup(_t("Use the breadcrumbs to return to your <b>task</b>.")),
            position: 'bottom'
        });

        const fsmTimerStopStepIndex = originalSteps.findIndex(step => step.id === 'fsm_save_timesheet');
        originalSteps.splice(fsmTimerStopStepIndex + 1, 0, {
            trigger: 'button[name="action_preview_worksheet"]',
            extra_trigger: '.o_form_project_tasks',
            content: markup(_t('<b>Review and sign</b> the <b>task report</b> with your customer.')),
            position: 'bottom',
        }, {
            trigger: 'a[data-bs-target="#modalaccept"]',
            extra_trigger: '.o_project_portal_sidebar',
            content: markup(_t('Invite your customer to <b>validate and sign your task report</b>.')),
            position: 'right',
            id: 'sign_report',
        }, {
            trigger: 'div[name="worksheet_map"] h5#task_worksheet',
            extra_trigger: '.o_project_portal_sidebar',
            content: ('"Worksheet" section is rendered'),
            auto: true,
        }, {
            trigger: 'div[name="worksheet_map"] div[class*="row"] div:not(:empty)',
            extra_trigger: '.o_project_portal_sidebar',
            content: ('At least a field is rendered'),
            auto: true,
        }, {
            trigger: '.o_web_sign_auto_button',
            extra_trigger: '.o_project_portal_sidebar',
            content: markup(_t('Save time by automatically generating a <b>signature</b>.')),
            position: 'right',
        }, {
            trigger: '.o_portal_sign_submit:enabled',
            extra_trigger: '.o_project_portal_sidebar',
            content: markup(_t('Validate the <b>signature</b>.')),
            position: 'left',
        }, {
            trigger: 'a:contains(Back to edit mode)',
            extra_trigger: '.o_project_portal_sidebar',
            content: markup(_t('Go back to your Field Service <b>task</b>.')),
            position: 'right',
        }, {
            trigger: 'button[name="action_send_report"]',
            extra_trigger: '.o_form_project_tasks',
            content: markup(_t('<b>Send your task report</b> to your customer.')),
            position: 'bottom',
        }, {
            trigger: 'button[name="action_send_mail"]',
            extra_trigger: '.o_form_project_tasks',
            content: markup(_t('<b>Send your task report</b> to your customer.')),
            position: 'right',
        });
        return originalSteps;
    }
});
