/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('planning_tour', {
    sequence: 120,
    url: '/web',
    rainbowManMessage: () => markup(_t("<b>Congratulations!</b></br> You are now a master of planning.")),
    steps: () => [
    {
        trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
        content: markup(_t("Let's start managing your employees' schedule!")),
        position: 'bottom',
    }, {
        trigger: ".o_gantt_button_add",
        content: markup(_t("Let's create your first <b>shift</b>. <i>Tip: use the (+) shortcut available on each cell of the Gantt view to save time.</i>")),
        position: "bottom",
    }, {
        trigger: ".o_field_widget[name='resource_id']",
        content: markup(_t("Assign a <b>resource</b>, or leave it open for the moment. <i>Tip: Create open shifts for the roles you will be needing to complete a mission. Then, assign those open shifts to the resources that are available.</i>")),
        position: "right",
    }, {
        trigger: ".o_field_widget[name='role_id'] .o_field_many2one_selection",
        content: markup(_t("Write the <b>role</b> your employee will perform (<i>e.g. Chef, Bartender, Waiter, etc.</i>). <i>Tip: Create open shifts for the roles you will be needing to complete a mission. Then, assign those open shifts to the resources that are available.</i>")),
        position: "right",
    }, {
        trigger: "button[special='save']",
        content: _t("Save this shift once it is ready."),
        position: "bottom",
    }, {
        trigger: ".o_gantt_pill:not(.o_gantt_consolidated_pill)",
        extra_trigger: '.o_action:not(.o_view_sample_data)',
        content: markup(_t("<b>Drag & drop</b> your shift to reschedule it. <i>Tip: hit CTRL (or Cmd) to duplicate it instead.</i> <b>Adjust the size</b> of the shift to modify its period.")),
        position: "bottom",
        run: "drag_and_drop_native .o_gantt_cell:nth-child(6)",
    }, {
        trigger: ".o_gantt_button_send_all",
        content: markup(_t("If you are happy with your planning, you can now <b>send</b> it to your employees.")),
        position: "bottom",
    }, {
        trigger: "button[name='action_check_emails']",
        content: markup(_t("<b>Publish & send</b> your employee's planning.")),
        position: "bottom",
    }, {
        trigger: "button.o_gantt_button_next",
        extra_trigger: "body:not(.modal-open)",
        content: markup(_t("Now that this week is ready, let's get started on <b>next week's schedule</b>.")),
        position: "bottom",
    }, {
        trigger: "button.o_gantt_button_copy_previous_week",
        content: markup(_t("Plan all of your shifts in one click by <b>copying the previous week's schedule</b>.")),
        position: "bottom",
    },
]});
