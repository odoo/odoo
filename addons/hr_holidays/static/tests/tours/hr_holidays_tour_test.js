import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("hr_holidays_tour_test", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            content: "Let's discover the Time Off app!",
            run: "click",
        },
        {
            trigger: ".o-dropdown-caret",
            content: "Click on this button to request time-off or allocation",
            run: "click",
        },
        {
            trigger: ".o-dropdown-item:nth-child(1)",
            content: "Click on this button to request a time-off",
            run: "click",
        },
        {
            trigger: 'div[name="work_entry_type_id"] input',
            content: "Let's try to create a sick time off, select it in the list",
            run: "click",
        },
        {
            trigger: ".ui-autocomplete .ui-menu-item a:contains('Guaranted monthly wage illness')",
            run: "click",
        },
        {
            trigger: "div[name=request_date_from] button",
            content: "You can select the period you need to take off",
            run: "click",
        },
        {
            content: "Click on the 22nd",
            trigger: ".o_date_item_cell:nth-child(31)",
            run: "click",
        },
        {
            content: "Click on the 25st",
            trigger: ".o_date_item_cell:nth-child(34)",
            run: "click",
        },
        {
            content: "click outside to go back to the time off record",
            trigger: ".modal-content",
            run: "click",
        },
        {
            trigger: 'div[name="name"] textarea',
            content: "Add some description for the leave",
            run: "click",
        },
        {
            trigger: "button:contains(Submit Request)",
            content: "Submit your request",
            run: "click",
        },
        {
            trigger: 'button[data-menu-xmlid="hr_holidays.menu_hr_holidays_management"]',
            content: "Let's go check it",
            run: "click",
        },
        {
            trigger: 'a[data-menu-xmlid="hr_holidays.menu_open_department_leave_approve"]',
            content: "Select Time Off",
            run: "click",
        },
        {
            content: "Switch to list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Select the request you just created",
            trigger: "table.o_list_table tr.o_data_row:nth-child(1)",
            run: "click",
        },
        {
            trigger: `tr.o_data_row:first:not(:has(button[name="action_approve"])),table tbody:not(tr.o_data_row)`,
            content:
                "Verify leave has been automatically approved as it has been created by an admin",
        },
    ],
});
