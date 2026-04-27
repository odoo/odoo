/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('planning_tour', {
    url: '/odoo',
    steps: () => [
    {
        trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
        content: markup(_t("Let's start managing your employees' schedule!")),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        isActive: ["mobile"],
        trigger: "tr td[data-time='08:00:00'].fc-timegrid-slot-lane",
        content: markup(_t("Let's schedule a <b>shift</b> for this time range.")),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        isActive: ["desktop"],
        trigger: ".o_gantt_button_add",
        content: markup(_t("Let's create your first <b>shift</b>. <i>Tip: use the (+) shortcut available on each cell of the Gantt view to save time.</i>")),
        tooltipPosition: "bottom",
        run: "click",
    }, {
        trigger: ".o_field_widget[name='resource_id']",
        content: markup(_t("Assign a <b>resource</b>, or leave it open for the moment. <i>Tip: Create open shifts for the roles you will be needing to complete a mission. Then, assign those open shifts to the resources that are available.</i>")),
        tooltipPosition: "right",
        run: "click",
    }, {
        trigger: ".o_field_widget[name='role_id'] .o_field_many2one_selection",
        content: markup(_t("Write the <b>role</b> your employee will perform (<i>e.g. Chef, Bartender, Waiter, etc.</i>). <i>Tip: Create open shifts for the roles you will be needing to complete a mission. Then, assign those open shifts to the resources that are available.</i>")),
        tooltipPosition: "right",
        run: "click",
    }, {
        trigger: "button[special='save']:enabled",
        content: _t("Save this shift once it is ready."),
        tooltipPosition: "bottom",
        run: "click",
    }, {
        isActive: ["mobile"],
        trigger: '.o_cp_switch_buttons .btn',
        content: markup(_t("Let's check out the Gantt view for cool features. Get ready to <b>share your schedule</b> and easily plan your shifts with just one click by <em>copying the previous week's schedule</em>.")),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        isActive: ["mobile"],
        trigger: 'span.o-dropdown-item:has(i.fa-tasks)',
        content: markup(_t("Let's check out the Gantt view for cool features. Get ready to <b>share your schedule</b> and easily plan your shifts with just one click by <em>copying the previous week's schedule</em>.")),
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        isActive: ["auto", "desktop"],
        trigger: ".o_action:not(.o_view_sample_data)",
    },
    {
        isActive: ["desktop"],
        trigger: ".o_gantt_pill:not(.o_gantt_consolidated_pill)",
        content: markup(_t("<b>Drag & drop</b> your shift to reschedule it. <i>Tip: hit CTRL (or Cmd) to duplicate it instead.</i> <b>Adjust the size</b> of the shift to modify its period.")),
        tooltipPosition: "bottom",
        run: "drag_and_drop .o_gantt_cell:nth-child(6)",
    }, {
        isActive: ["mobile"],
        trigger: ".o_control_panel .dropdown-toggle",
        content: _t("Share the schedule with your team by publishing and sending it. Open the menu to access this option."),
        tooltipPosition: "bottom",
        run: "click",
    }, {
        isActive: ["mobile"],
        trigger: ".o_gantt_button_send_all",
        content: markup(_t("If you are happy with your planning, you can now <b>send</b> it to your employees.")),
        tooltipPosition: "right",
        run: "click",
    }, {
        isActive: ["desktop"],
        trigger: ".o_gantt_button_send_all",
        content: markup(_t("If you are happy with your planning, you can now <b>send</b> it to your employees.")),
        tooltipPosition: "bottom",
        run: "click",
    }, {
        isActive: ["mobile"],
        trigger: "button[name='action_check_emails']",
        content: markup(_t("If you are happy with your planning, you can now <b>send</b> it to your employees.")),
        tooltipPosition: "right",
        run: "click",
    }, {
        isActive: ["desktop"],
        trigger: "button[name='action_check_emails']",
        content: markup(_t("<b>Publish & send</b> your employee's planning.")),
        tooltipPosition: "bottom",
        run: "click",
    }, {
        trigger: ".o_gantt_renderer_controls button i.fa-arrow-right",
        content: markup(_t("Now that this week is ready, let's get started on <b>next week's schedule</b>.")),
        tooltipPosition: "bottom",
        run: "click",
    }, {
        trigger: ".o_control_panel .dropdown-toggle",
        content: markup(_t("Plan your shifts in one click by <b>copying the schedule from the previous week</b>. Open the menu to access this option.")),
        tooltipPosition: "bottom",
        run: "click",
    }, {
        trigger: ".o_gantt_button_copy_previous_week",
        content: markup(_t("Plan your shifts in one click by <b>copying the schedule from the previous week</b>.")),
        tooltipPosition: "right",
        run: "click",
    },
]});
