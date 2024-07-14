/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('industry_fsm_tour', {
    sequence: 90,
    url: "/web",
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="industry_fsm.fsm_menu_root"]',
    content: markup(_t('Ready to <b>manage your onsite interventions</b>? <i>Click Field Service to start.</i>')),
    position: 'bottom',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_fsm_kanban',
    content: markup(_t('Let\'s create your first <b>task</b>.')),
    position: 'bottom',
}, {
    trigger: 'h1 div[name="name"] > div > textarea',
    extra_trigger: '.o_form_editable',
    content: markup(_t('Give it a <b>title</b> <i>(e.g. Boiler maintenance, Air-conditioning installation, etc.).</i>')),
    position: 'right',
    width: 200,
}, {
    trigger: ".o_field_widget[name=partner_id]",
    content: markup(_t('Select the <b>customer</b> for your task.')),
    position: "right",
    run() {
        document.querySelector('.o_field_widget[name="partner_id"] input').click();
    }
}, {
    trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
    auto: true,
}, {
    trigger: 'button[name="action_timer_start"]',
    extra_trigger: '.o_form_project_tasks',
    content: markup(_t('Launch the timer to <b>track the time spent</b> on your task.')),
    position: "bottom",
    id: 'fsm_start',
}, {
    trigger: 'button[name="action_timer_stop"]',
    content: markup(_t('Stop the <b>timer</b> when you are done.')),
    position: 'bottom',
}, {
    trigger: 'button[name="save_timesheet"]',
    content: markup(_t('Confirm the <b>time spent</b> on your task. <i>Tip: note that the duration has automatically been rounded to 15 minutes.</i>')),
    position: 'bottom',
    id: "fsm_save_timesheet"
}, {
    trigger: "button[name='action_fsm_validate']",
    extra_trigger: '.o_form_project_tasks',
    content: markup(_t('Let\'s <b>mark your task as done!</b> <i>Tip: when doing so, your stock will automatically be updated, and your task will be closed.</i>')),
    position: 'bottom',
}, {
    // check the task is marked as done
    trigger: "div[name='state'] .btn-outline-success",
    auto: true,
    isCheck: true,
    id: 'fsm_invoice_create',
}]});
