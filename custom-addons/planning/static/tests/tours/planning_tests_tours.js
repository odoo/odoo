/** @odoo-module **/

import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('planning_test_tour', {
    url: '/web',
    test: true,
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Let's start managing your employees' schedule!",
    position: 'bottom',
}, {
    trigger: ".o_gantt_button_add",
    content: markup("Let's create your first <b>shift</b>."),
    id: 'project_planning_start',
}, {
    trigger: ".o_field_widget[name='resource_id'] input",
    content: markup("Assign this shift to your <b>resource</b>, or leave it open for the moment."),
    run: 'text Aaron',
}, {
    trigger: ".o-autocomplete--dropdown-item > a:contains('Aaron')",
    auto: true,
    in_modal: false,
}, {
    trigger: ".o_field_widget[name='role_id'] input",
    content: markup("Select the <b>role</b> your employee will have (<i>e.g. Chef, Bartender, Waiter, etc.</i>)."),
    run: 'text Developer',
}, {
    trigger: ".o-autocomplete--dropdown-item > a:contains('Developer')",
    auto: true,
    in_modal: false,
}, {
    trigger: ".o_field_widget[name='start_datetime'] input",
    content: "Set start datetime",
    run: function (actions) {
        const input = this.$anchor[0];
        input.value = input.value.replace(/(\d{2}:){2}\d{2}/g, '08:00:00');
        input.dispatchEvent(new InputEvent('input', {
            bubbles: true,
        }));
        input.dispatchEvent(new Event("change", { bubbles: true, cancelable: false }));
    }
}, {
    trigger: "input[data-field=end_datetime]",
    content: "Set end datetime",
    run: function (actions) {
        const input = this.$anchor[0];
        input.value = input.value.replace(/(\d{2}:){2}\d{2}/g, '11:59:59');
        input.dispatchEvent(new InputEvent('input', {
            bubbles: true,
        }));
        input.dispatchEvent(new Event("change", { bubbles: true, cancelable: false }));
    }
}, {
    trigger: "div[name='template_creation'] input",
    content: "Save this shift as a template",
    run: function (actions) {
        if (!this.$anchor.prop('checked')) {
            actions.click(this.$anchor);
        }
    },
}, {
    trigger: "button[special='save']",
    content: "Save this shift once it is ready.",
}, {
    trigger: ".o_gantt_pill :contains('11:59')",
    content: markup("<b>Drag & drop</b> your shift to reschedule it. <i>Tip: hit CTRL (or Cmd) to duplicate it instead.</i> <b>Adjust the size</b> of the shift to modify its period."),
    auto: true,
    run: function () {
        if (this.$anchor.length) {
            const expected = "8:00 AM - 11:59 AM (4h)";
            // Without the replace below, this step could break since luxon
            // (via Intl) uses sometimes U+202f instead of a simple space.
            // Note: U+202f is a narrow non-break space.
            const actual = this.$anchor[0].textContent.replace(/\u202f/g, " ");
            if (!actual.startsWith(expected)) {
                console.error("Test in gantt view doesn't start as expected. Expected : '" + expected + "', actual : '" + actual + "'");
            }
        } else {
            console.error("Not able to select pill ending at 11h59");
        }
    }
}, {
    trigger: ".o_gantt_button_send_all",
    content: markup("If you are happy with your planning, you can now <b>send</b> it to your employees."),
}, {
    trigger: "button[name='action_check_emails']",
    content: markup("<b>Publish & send</b> your planning to make it available to your employees."),
}, {
    trigger: ".o_gantt_row_header:contains('Aaron') .o_gantt_progress_bar",
    content: "See employee progress bar",
    auto: true,
    run: function () {
        const $progressbar = this.$anchor;
        if ($progressbar.length) {
            if ($progressbar[0].querySelector("span").style.width === '') {
                console.error("Progress bar should be displayed");
            }
            if (!$progressbar[0].classList.contains("o_gantt_group_success")) {
                console.error("Progress bar should be displayed in success");
            }
        } else {
            console.error("Not able to select progressbar");
        }
    }
}, {
    trigger: ".o_gantt_button_copy_previous_week",
    content: "Copy previous week if you want to follow previous week planning schedule",
    run: 'click',
}, {
    id: "planning_check_format_step",
    trigger: ".o_gantt_pill span:contains(Developer)",
    content: "Check naming format of resource and role when grouped",
    auto: true,
    run: function () {}
}, {
    trigger: ".o_gantt_button_auto_plan",
    content: "Click on Auto Plan button to assign open shifts to employees",
    run: 'click',
}, {
    id: "planning_check_format_step",
    trigger: ".o_gantt_pill.opacity-25",
    content: "Check that the filter is applied",
    auto: true,
    run: function () {},
}]});

registry.category("web_tour.tours").add('planning_shift_switching_backend', {
    url: '/web',
    test: true,
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Get in the planning app",
}, {
    trigger: '.o_gantt_pill :contains("bert")',
    content: "Click on one of your shifts in the gantt view",
},
{
    trigger: ".popover-footer button",
    content: "Click on the 'Edit' button in the popover",
    run: 'click',
},
{
    trigger: 'button[name="action_switch_shift"]',
    content: "Click on the 'Switch Shift' button on the Gantt Form view modal",
}, {
    trigger: 'div.o_view_scale_selector > .scale_button_selection',
    content: 'Toggle the view scale selector',
}, {
    trigger: 'div.o_view_scale_selector > .dropdown-menu',
    content: 'Click on the dropdown button to change the scale of the gantt view',
    extra_trigger: 'div.o_view_scale_selector .o_scale_button_day',
}, {
    trigger: '.o_gantt_pill :contains("bert")',
    content: "Click on the unwanted shift in the gantt view again",
},
{
    trigger: ".popover-footer button",
    content: "Click again on the 'Edit' button in the popover",
    run: 'click',
},
{
    trigger: '.alert-warning:contains("The employee assigned would like to switch shifts with someone else.")',
    content: "Check that the warning has been shown",
}, {
    trigger: '.btn-close',
    content: "Click on the close button to hide the shift form modal",
}, {
    trigger: '.o_planning_gantt',
    isCheck: true,
}]});

registry.category("web_tour.tours").add('planning_assigning_unwanted_shift_backend', {
    url: '/web',
    test: true,
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Get in the planning app",
}, {
    trigger: '.o_gantt_pill :contains("bert")',
    content: "Click on the unwanted shift of the employee",
},
{
    trigger: ".popover-footer button",
    content: "Click on the 'Edit' button in the popover",
    run: 'click',
},
{
    trigger: ".o_field_widget[name='resource_id'] input",
    content: "Assign this shift to another employee.",
    run: 'text joseph',
}, {
    trigger: ".o-autocomplete--dropdown-item > a:contains('joseph')",
    auto: true,
    in_modal: false,
}, {
    trigger: "button[special='save']",
    content: "Save this shift once it is ready.",
}, {
    trigger: '.o_gantt_pill :contains("joseph")',
    content: "Click again on the newly assigned shift",
}, {
    trigger: '.o_popover',
    content: "Check the popover opened",
    isCheck: true,
}]});
