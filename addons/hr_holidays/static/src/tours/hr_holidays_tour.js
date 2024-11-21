/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const leaveType = "NotLimitedHR";
const leaveDateFrom = "01/17/2022";
const leaveDateTo = "01/17/2022";
const description = "Days off";

registry.category("web_tour.tours").add("hr_holidays_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            content: _t("Let's discover the Time Off application"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "button.btn-time-off",
            content: _t("Click on any date or on this button to request a time-off"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'div[name="holiday_status_id"] input',
            content: _t("Let's try to create a Sick Time Off, select it in the list"),
            run: `edit ${leaveType.slice(0, leaveType.length - 1)}`,
        },
        {
            isActive: ["auto"],
            trigger: `.ui-autocomplete .ui-menu-item a:contains("${leaveType}")`,
            run: "click",
        },
        {
            trigger: `.o_field_widget[name='holiday_status_id'] input:value("${leaveType}")`,
        },
        {
            trigger: "input[data-field=request_date_from]",
            content: _t(
                "You can select the period you need to take off, from start date to end date"
            ),
            tooltipPosition: "right",
            run: `edit ${leaveDateFrom}`,
        },
        {
            trigger: "input[data-field=request_date_to]",
            content: _t(
                "You can select the period you need to take off, from start date to end date"
            ),
            tooltipPosition: "right",
            run: `edit ${leaveDateTo}`,
        },
        {
            trigger: 'div[name="name"] textarea',
            content: _t("Add some description for the people that will validate it"),
            run: `edit ${description}`,
            tooltipPosition: "right",
        },
        {
            trigger: `button:contains(${_t("Save")})`,
            content: _t("Submit your request"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'button[data-menu-xmlid="hr_holidays.menu_hr_holidays_management"]',
            content: _t("Let's go validate it"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'a[data-menu-xmlid="hr_holidays.menu_open_department_leave_approve"]',
            content: _t("Select Time Off"),
            tooltipPosition: "right",
            run: "click",
        },
        {
            tooltipPosition: "bottom",
            content: _t("Select the request you just created"),
            trigger: "table.o_list_table tr.o_data_row:eq(0)",
            run: "click",
        },
        {
            trigger: 'button[name="action_approve"]',
            content: _t("Let's approve it"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: `tr.o_data_row:first:not(:has(button[name="action_approve"])),table tbody:not(tr.o_data_row)`,
            content: "Verify leave is approved",
        },
    ],
});
