import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("hr_holidays_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            content: markup(_t("Let's discover the <strong>Time Off</strong> app!")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "button.btn-time-off",
            content: _t("Click on this button to request a time-off"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'div[name="holiday_status_id"] input',
            content: _t("Let's try to create a Sick Time Off, select it in the list"),
            run: "click",
        },
        {
            trigger: ".ui-autocomplete .ui-menu-item a:contains('Sick Time Off')",
            tooltipPosition: "right",
            run: "click",
        },
        {
            trigger: "input[data-field=request_date_from]",
            content: _t(
                "You can select the period you need to take off"
            ),
            tooltipPosition: "right",
            run: "click",
        },
        {
            content: _t("Click on the 22nd"),
            trigger: '.o_date_item_cell:nth-child(31)',
            run: "click"
        },
        {
            content: _t("Click on the 25st"),
            trigger: '.o_date_item_cell:nth-child(34)',
            run: "click"
        },
        {
            content: "click outside to go back to the time off record",
            trigger: '.modal-content',
            run: "click",
        },
        {
            trigger: 'div[name="name"] textarea',
            content: _t("Add some description for the people that will validate it"),
            run: "click",
            tooltipPosition: "right",
        },
        {
            trigger: `button:contains(${_t("Submit Request")})`,
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
            content: "Switch to list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            tooltipPosition: "bottom",
            content: _t("Select the request you just created"),
            trigger: "table.o_list_table tr.o_data_row:nth-child(1)",
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
