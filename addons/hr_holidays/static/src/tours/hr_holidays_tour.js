/** @odoo-module **/
import tour from 'web_tour.tour';
import { _t } from 'web.core';
import session from 'web.session';

const leaveType = "NotLimitedHR";
const leaveDateFrom = "01/17/2022";
const leaveDateTo = "01/17/2022";
const description = 'Days off';

tour.register('hr_holidays_tour', {
    url: '/web',
    rainbowManMessage: _t("Congrats, we can see that your request has been validated."),
    test: false
}, [
    tour.stepUtils.showAppsMenuItem(), 
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
        trigger: '.o_field_widget[name="holiday_status_id"]',
        content: _t("Let's try to create a Sick Time Off, select it in the list"),
        position: 'right',
        run: function(actions) {
            actions.text(leaveType, this.$anchor.find('input'));
        }
    },
    {
        trigger: ".ui-menu-item > a",
        auto: true,
        in_modal: false
    },
    {
        trigger: 'input[name="request_date_from"]',
        content: _t("You can select the period you need to take off, from start date to end date"),
        position: 'right',
        run: function(actions) {
            this.$anchor.val(leaveDateFrom);
            this.$anchor.trigger("change");
        }
    },
    {
        trigger: 'input[name="request_date_to"]',
        content: _t("You can select the period you need to take off, from start date to end date"),
        position: 'right',
        run: function(actions) {
            this.$anchor.val(leaveDateTo);
            this.$anchor.trigger("change");
        },
        auto: true
    },
    {
        trigger: 'textarea[name="name"]',
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
        trigger: 'button[data-menu-xmlid="hr_holidays.menu_hr_holidays_approvals"]',
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
            const createdRow = rows.filter((i, row) => {
                const el = $(row);
                return el.find(`div[name="all_employee_ids"]:contains("${session.name}")`).length &&
                el.find(`td[name="name"]:contains("${description}")`).length &&
                el.find(`td[name="holiday_status_id"]:contains("${leaveType}")`).length &&
                el.find(`td[name="date_from"]:contains("${leaveDateFrom}")`).length &&
                el.find(`td[name="date_to"]:contains("${leaveDateTo}")`).length;
            });
            actions.click(createdRow);
        }
    },
    {
        trigger: 'button[name="action_approve"]',
        content: _t("Let's approve it"),
        position: 'bottom'
    },
    {
        trigger: 'a[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
        content: _t("State is now confirmed. We can go back to the calendar"),
        position: 'bottom'
    }
]);
