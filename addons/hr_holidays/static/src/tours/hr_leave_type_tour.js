/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const leaveType1 = "leave_type_1";
const leaveType2 = "leave_type_2";
const leaveType3 = "leave_type_3";
const noRecords = "No Records";
const company2 = "company_2";
const firstLeaveDateFrom = "01/17/2022";
const firstLeaveDateTo = "01/17/2022";
const secondLeaveDateFrom = "01/18/2022";
const secondLeaveDateTo = "01/18/2022";

registry.category("web_tour.tours").add("hr_leave_type_tour", {
    url: "/web",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            content: "Open the time-off application",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'button[data-menu-xmlid="hr_holidays.menu_hr_holidays_management"]',
            content: "Open the management menu",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'a[data-menu-xmlid="hr_holidays.menu_open_department_leave_approve"]',
            content: "Choose Time Off from the menu",
            tooltipPosition: "right",
            run: "click",
        },
        {
            trigger: "button.o-kanban-button-new",
            content: "Create a new time-off request",
            tooltipPosition: "bottom",
            run: "click",
        },
        // Check if a time-off could be requested using leave_type_1 as company_1 is selected by default.
        {
            trigger: 'div[name="holiday_status_id"] input',
            content: "Create a time-off using leave_type_1. Select it from the list",
            tooltipPosition: "bottom",
            run: `edit ${leaveType1}`,
        },
        {
            isActive: ["auto"],
            trigger: `.ui-autocomplete .ui-menu-item a:contains("${leaveType1}")`,
            run: "click",
        },
        {
            trigger: `.o_field_widget[name='holiday_status_id'] input:value("${leaveType1}")`,
        },
        // Check that a time-off cannot be requested using leave_type_2 as company_2 is not selected.
        {
            trigger: 'div[name="holiday_status_id"] input',
            content: "Try to select leave_type_2 from the list. It shouldn't be present",
            tooltipPosition: "bottom",
            run: `edit ${leaveType2}`,
        },
        {
            trigger: `.ui-autocomplete .ui-menu-item span:contains('${noRecords}')`,
        },
        // Check if a time-off could be requested using leave_type_3
        {
            trigger: 'div[name="holiday_status_id"] input',
            content: "Select leave_type_3 from the list",
            tooltipPosition: "bottom",
            run: `edit ${leaveType3}`,
        },
        {
            isActive: ["auto"],
            trigger: `.ui-autocomplete .ui-menu-item a:contains("${leaveType3}")`,
            run: "click",
        },
        {
            trigger: `.o_field_widget[name='holiday_status_id'] input:value("${leaveType3}")`,
        },
        {
            trigger: "div[name=request_date_from] button",
            content: "Let's change the start date of the leave",
            run: "click",
        },
        {
            trigger: "input[data-field=request_date_from]",
            content: "Select the start date of the leave",
            tooltipPosition: "right",
            run: `edit ${firstLeaveDateFrom}`,
        },
        {
            trigger: "button[data-field=request_date_to]",
            content: "Let's change the end date of the leave",
            run: "click",
        },
        {
            trigger: "input[data-field=request_date_to]",
            content: "Select the end date of the leave",
            tooltipPosition: "right",
            run: `edit ${firstLeaveDateTo} && press Enter`,
        },
        ...stepUtils.saveForm(),
        {
            trigger: 'button[name="action_approve"]',
            content: "Approve the leave",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'button[name="action_cancel"]',
            content:
                "Make sure that the leave is approved by checking that the cancel button appears",
        },
        {
            trigger: ".o_switch_company_menu button",
            content: "Open the companies selection menu",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: `.o_switch_company_item:contains("${company2}") [role=menuitemcheckbox]`,
            content: "Select company_2",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_switch_company_menu_buttons button:contains(Confirm)",
            content: "Confirm the company selection",
            tooltipPosition: "bottom",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "button.o_form_button_create",
            content: "Create a new time-off request",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'div[name="holiday_status_id"] input',
            content:
                "Select leave_type_2 from the list. It should be available now because company_2 is selected",
            tooltipPosition: "bottom",
            run: `edit ${leaveType2}`,
        },
        {
            isActive: ["auto"],
            trigger: `.ui-autocomplete .ui-menu-item a:contains("${leaveType2}")`,
            run: "click",
        },
        {
            trigger: `.o_field_widget[name='holiday_status_id'] input:value("${leaveType2}")`,
            tooltipPosition: "bottom",
        },
        {
            trigger: "div[name=request_date_from] button",
            content: "Let's change the start date of the leave",
            run: "click",
        },
        {
            trigger: "input[data-field=request_date_from]",
            content: "Select the start date of the leave",
            tooltipPosition: "right",
            run: `edit ${secondLeaveDateFrom}`,
        },
        {
            trigger: "button[data-field=request_date_to]",
            content: "Let's change the end date of the leave",
            run: "click",
        },
        {
            trigger: "input[data-field=request_date_to]",
            content: "Select the end date of the leave",
            tooltipPosition: "right",
            run: `edit ${secondLeaveDateTo} && press Enter`,
        },
        ...stepUtils.saveForm(),
        {
            trigger: 'button[name="action_approve"]',
            content: "Approve the leave",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'button[name="action_cancel"]',
            content:
                "Make sure that the leave is approved by checking that the cancel button appears",
        },
    ],
});
