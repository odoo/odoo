/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const leaveType = "NotLimitedHR";
const leaveDateFrom = "01/17/2022";
const leaveDateTo = "01/17/2022";
const description = 'Days off';

registry.category("web_tour.tours").add('hr_holidays_tour', {
    url: '/web',
    rainbowManMessage: _t("Congrats, we can see that your request has been validated."),
    test: false,
    steps: () => [
    stepUtils.showAppsMenuItem(),
    {
        trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
        content: _t("Let's discover the Time Off application"),
        position: 'bottom',
    },
    {
        trigger: 'button.btn-time-off',
        content: _t("Click on any date or on this button to request a time-off"),
        position: 'bottom',
    },
    {
        trigger: 'div[name="holiday_status_id"] input',
        content: _t("Let's try to create a Sick Time Off, select it in the list"),
        run: `text ${leaveType.slice(0, leaveType.length - 1)}`,
    },
    {
        trigger: `.ui-autocomplete .ui-menu-item a:contains("${leaveType}")`,
        run: "click",
        auto: true,
        in_modal: false,
    },
    {
        trigger: 'input[data-field=request_date_from]',
        extra_trigger: `.o_field_widget[name='holiday_status_id'] input:propValue("${leaveType}")`,
        content: _t("You can select the period you need to take off, from start date to end date"),
        position: 'right',
        run: `text ${leaveDateFrom}`,
    },
    {
        trigger: 'input[data-field=request_date_to]',
        content: _t("You can select the period you need to take off, from start date to end date"),
        position: 'right',
        run: `text ${leaveDateTo}`,
    },
    {
        trigger: 'div[name="name"] textarea',
        content: _t("Add some description for the people that will validate it"),
        run: `text ${description}`,
        position: 'right'
    },
    {
        trigger: `button:contains(${_t('Save')})`,
        content: _t("Submit your request"),
        position: 'bottom',
    },
    {
        trigger: 'button[data-menu-xmlid="hr_holidays.menu_hr_holidays_management"]',
        content: _t("Let's go validate it"),
        position: 'bottom'
    },
    {
        trigger: 'a[data-menu-xmlid="hr_holidays.menu_open_department_leave_approve"]',
        content: _t("Select Time Off"),
        position: 'right'
    },
    {
        trigger: 'table.o_list_table',
        content: _t("Select the request you just created"),
        position: 'bottom',
        run: function(actions) {
            const rows = this.$anchor.find('tr.o_data_row');
            actions.click(rows[0]);
        }
    },
    {
        trigger: 'button[name="action_approve"]',
        content: _t("Let's approve it"),
        position: 'bottom',
    },
    {
        trigger: `tr.o_data_row:first:not(:has(button[name="action_approve"])),table tbody:not(tr.o_data_row)`,
        content: "Verify leave is approved",
        auto: true,
        isCheck: true,
    }
]});
