/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("industry_fsm_tour", {
    url: "/odoo",
    steps: () => [
        {
    trigger: '.o_app[data-menu-xmlid="industry_fsm.fsm_menu_root"]',
    content: markup(_t('Ready to <b>manage your onsite interventions</b>? <i>Click Field Service to start.</i>')),
    tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: ".o_fsm_kanban",
        },
        {
    trigger: '.o-kanban-button-new',
    content: markup(_t('Let\'s create your first <b>task</b>.')),
    tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: ".o_form_editable",
        },
        {
    trigger: 'h1 div[name="name"] > div > textarea',
    content: markup(_t('Give it a <b>title</b> <i>(e.g. Boiler maintenance, Air-conditioning installation, etc.).</i>')),
    tooltipPosition: 'right',
            run: "edit Test",
        },
        {
    trigger: ".o_field_widget[name=partner_id]",
    content: markup(_t('Select the <b>customer</b> for your task.')),
    tooltipPosition: "right",
        },
        {
            trigger: '.o_field_widget[name="partner_id"] input',
            content: markup(_t('Select the <b>customer</b> for your task.')),
            tooltipPosition: "right",
            run: "click",
        },
        {
            isActive: ["auto"],
    trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
            run: "click",
        },
        {
            trigger: ".o_form_project_tasks",
        },
        {
    trigger: 'button[name="action_timer_start"]',
    content: markup(_t('Launch the timer to <b>track the time spent</b> on your task.')),
    tooltipPosition: "bottom",
    id: 'fsm_start',
            run: "click",
        },
        {
    trigger: 'button[name="action_timer_stop"]',
    content: markup(_t('Stop the <b>timer</b> when you are done.')),
    tooltipPosition: 'bottom',
            run: "click",
        },
        {
    trigger: 'button[name="save_timesheet"]',
    content: markup(_t('Confirm the <b>time spent</b> on your task. <i>Tip: note that the duration has automatically been rounded to 15 minutes.</i>')),
    tooltipPosition: 'bottom',
            id: "fsm_save_timesheet",
            run: "click",
        },
        {
            trigger: ".o_form_project_tasks",
        },
        {
    trigger: "button[name='action_fsm_validate']",
    content: markup(_t('Let\'s <b>mark your task as done!</b> <i>Tip: when doing so, your stock will automatically be updated, and your task will be closed.</i>')),
    tooltipPosition: 'bottom',
            run: "click",
        },
        {
            // check the task is marked as done
            trigger: "div[name='state'] .btn-outline-success",
            id: "fsm_invoice_create",
        },
    ],
});
