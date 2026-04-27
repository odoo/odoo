/** @odoo-module **/

import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
const today = luxon.DateTime.now();

registry.category("web_tour.tours").add('planning_test_tour', {
    url: '/odoo',
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Let's start managing your employees' schedule!",
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o_gantt_button_add",
    content: markup("Let's create your first <b>shift</b>."),
    id: 'project_planning_start',
    run: "click",
}, {
    trigger: ".o_field_widget[name='resource_id'] input",
    content: markup("Assign this shift to your <b>resource</b>, or leave it open for the moment."),
    run: "edit Aaron",
}, {
    isActive: ["auto"],
    trigger: ".o-autocomplete--dropdown-item > a:contains('Aaron')",
    run: "click",
}, {
    trigger: ".o_field_widget[name='role_id'] input",
    content: markup("Select the <b>role</b> your employee will have (<i>e.g. Chef, Bartender, Waiter, etc.</i>)."),
    run: "edit Developer",
}, {
    isActive: ["auto"],
    trigger: ".o-autocomplete--dropdown-item > a:contains('Developer')",
    run: "click",
}, {
    trigger: ".o_field_widget[name='start_datetime'] input",
    content: "Set start datetime",
    run: `edit ${today.toFormat("MM/dd/yyyy")} 09:00`,
}, {
    trigger: "input[data-field=end_datetime]",
    content: "Set end datetime",
    run: `edit ${today.toFormat("MM/dd/yyyy")} 11:59`,
}, {
    trigger: "button[name='action_save_template']",
    content: "Save this shift as a template",
    run: "click",
}, {
    trigger: "button[special='save']:enabled",
    content: "Save this shift once it is ready.",
    run: "click",
}, {
    isActive: ["auto"],
    trigger: ".o_gantt_pill :contains('11:59')",
    content: markup("<b>Drag & drop</b> your shift to reschedule it. <i>Tip: hit CTRL (or Cmd) to duplicate it instead.</i> <b>Adjust the size</b> of the shift to modify its period."),
    run: function () {
        const expected = "9:00 AM - 11:59 AM";
        // Without the replace below, this step could break since luxon
        // (via Intl) uses sometimes U+202f instead of a simple space.
        // Note: U+202f is a narrow non-break space.
        const actual = this.anchor.textContent.replace(/\u202f/g, " ");
        if (!actual.startsWith(expected)) {
            console.error("Test in gantt view doesn't start as expected. Expected : '" + expected + "', actual : '" + actual + "'");
        }
    }
}, {
    isActive: ["mobile"],
    trigger: ".o_control_panel .dropdown-toggle",
    content: "Share the schedule with your team by publishing and sending it. Open the menu to access this option.",
    tooltipPosition: "top",
    run: "click",
}, {
    trigger: ".o_gantt_button_send_all",
    content: markup("If you are happy with your planning, you can now <b>send</b> it to your employees."),
    run: "click",
}, {
    trigger: "button[name='action_check_emails']",
    content: markup("<b>Publish & send</b> your planning to make it available to your employees."),
    run: "click",
}, {
    isActive: ["auto"],
    trigger: ".o_gantt_row_header:contains('Aaron') .o_gantt_progress_bar",
    content: "See employee progress bar",
    run: function () {
        if (this.anchor.querySelector("span").style.width === '') {
            console.error("Progress bar should be displayed");
        }
        if (!this.anchor.classList.contains("o_gantt_group_success")) {
            console.error("Progress bar should be displayed in success");
        }
    }
}, {
    trigger: ".o_control_panel .dropdown-toggle",
    content: "Plan your shifts in one click by copying the schedule from the previous week. Open the menu to access this option.",
    tooltipPosition: "top",
    run: "click",
}, {
    trigger: ".o_gantt_button_copy_previous_week",
    content: "Copy previous week if you want to follow previous week planning schedule",
    tooltipPosition: "right",
    run: 'click',
}, {
    id: "planning_check_format_step",
    trigger: ".o_gantt_pill span:contains(Developer)",
    content: "Check naming format of resource and role when grouped",
}, {
    trigger: ".o_control_panel .dropdown-toggle",
    content: "Automatically match open shifts and sales orders to the right people, taking into account their working hours, roles, availability, and time off. Open the menu to access this option.",
    tooltipPosition: "top",
    run: "click",
}, {
    trigger: ".o_gantt_button_auto_plan",
    content: "Click on Auto Plan button to assign open shifts to employees",
    tooltipPosition: "right",
    run: 'click',
}, {
    id: "planning_check_format_step",
    trigger: ".o_gantt_pill.opacity-25",
    content: "Check that the filter is applied",
}]});

registry.category("web_tour.tours").add('planning_test_tour_no_email', {
    url: '/odoo',
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Open the planning app, should land in the gantt view",
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o_gantt_button_send_all",
    content: "Click on the 'Publish' button on the top-left of the gantt view to publish the draft shifts",
    run: "click",
}, {
    trigger: "button[name='action_check_emails']",
    content: "The 'No Email Address for some Empoyees' wizard should be raised since we haven't given an employee email",
    run: "click",
}, {
    trigger: "td[data-tooltip='Aaron']",
}, {
    trigger: "button[special='cancel']",
    run: "click",
}, {
    trigger: '.o_gantt_pill :contains("aaron_role")',
    content: "Click on the shift of Aaron",
    run: "click",
}, {
    trigger: ".popover-footer button",
    content: "Click on the 'Edit' button in the popover",
    run: "click",
}, {
    trigger: "button[name='action_send']",
    content: "Click on the 'Publish' button",
    run: "click",
}, {
    trigger: ".modal-content label:contains('Work Email')",
    content: "The 'Add Work Email' wizard should be raised",
},]});

registry.category("web_tour.tours").add('planning_shift_switching_backend', {
    url: '/odoo',
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Get in the planning app",
    run: "click",
}, {
    trigger: '.o_gantt_pill :contains("test_role")',
    content: "Click on one of your shifts in the gantt view",
    run: "click",
},
{
    trigger: ".popover-footer button",
    content: "Click on the 'Edit' button in the popover",
    run: 'click',
},
{
    trigger: 'button[name="action_switch_shift"]',
    content: "Click on the 'Switch Shift' button on the Gantt Form view modal",
    run: "click",
}, {
    trigger: '.o_gantt_pill :contains("test_role")',
    content: "Click on the unwanted shift in the gantt view again",
    run: "click",
},
{
    trigger: ".popover-footer button",
    content: "Click again on the 'Edit' button in the popover",
    run: 'click',
},
{
    trigger: '.alert-warning:contains("The employee assigned would like to switch shifts with someone else.")',
    content: "Check that the warning has been shown",
    run: "click",
}, {
    trigger: '.btn-close',
    content: "Click on the close button to hide the shift form modal",
    run: "click",
}, {
    trigger: '.o_planning_gantt',
}]});

registry.category("web_tour.tours").add('planning_assigning_unwanted_shift_backend', {
    url: '/odoo',
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Get in the planning app",
    run: "click",
}, {
    trigger: '.o_gantt_pill :contains("test_role")',
    content: "Click on the unwanted shift of the employee",
    run: "click",
},
{
    trigger: ".popover-footer button",
    content: "Click on the 'Edit' button in the popover",
    run: 'click',
},
{
    trigger: ".o_field_widget[name='resource_id'] input",
    content: "Assign this shift to another employee.",
    run: "edit bety",
}, {
    isActive: ["auto"],
    trigger: ".o-autocomplete--dropdown-item > a:contains('bety')",
    run: "click",
}, {
    trigger: ".modal button[special='save']:enabled",
    content: "Save this shift once it is ready.",
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
{
    trigger: '.o_gantt_pill :contains("test_role")',
    content: "Click again on the newly assigned shift",
    run: "click",
}, {
    trigger: '.o_popover',
    content: "Check the popover opened",
}]});
