/** @odoo-module */

import { setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";


let serverData;

QUnit.module("leave dashboard", {
    beforeEach() {
        setupViewRegistries();

        serverData = {
            views: {
                "hr.leave,false,calendar": `
                <calendar js_class="time_off_calendar_dashboard"
                    string="Time Off Request"
                    form_view_id="%(hr_holidays.hr_leave_view_form_dashboard_new_time_off)d"
                    event_open_popup="true"
                    date_start="date_from"
                    date_stop="date_to"
                    quick_create="0"
                    show_unusual_days="True"
                    color="color"
                    hide_time="True"
                    mode="year"
                    all_day="last_several_days">
                <field name="name"/>
                <field name="holiday_status_id" filters="1" invisible="1" color="color"/>
                <field name="state" invisible="1"/>
            </calendar>`,
            "hr.leave,false,search": "<search/>",
            },
            models: {
                "hr.leave.type": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        color: { string: "Color", type: "int" },
                    },
                },
                "hr.leave.allocation": {
                    fields: {
                        employee_id: { string: "Employee", type: "many2one", relation: "employee" },
                        date_from: { string: "From", type: "datetime" },
                        holiday_status_id: {
                            string: "Leave type",
                            type: "many2one",
                            relation: "hr.leave.type",
                        },
                        state: { 
                            string: "State", 
                            type: "selection", 
                            selection: [
                                ["confirm", "To Approve"],
                                ["refuse", "Refused"],
                                ["validate", "Validated"],
                            ],
                        },
                        number_of_days: { string: "Number of Days", type: "integer" },
                        allocation_type: { 
                            string: "Allocation Type", 
                            type: "selection", 
                            selection: [
                                ["regular", "Regular Allocation"],
                                ["accrual", "Accrual Allocation"],
                            ],
                        },
                        holiday_type: { 
                            string: "Allocation Mode", 
                            type: "selection", 
                            selection: [
                                ["employee", "By Employee"],
                                ["company", "By Company"],
                                ["department", "By Department"],
                                ["category", "By Employee Tag"],
                            ],
                        },
                    },
                },
                "hr.leave": {
                    fields: {
                        employee_id: { string: "Employee", type: "many2one", relation: "employee" },
                        department_id: {
                            string: "Department",
                            type: "many2one",
                            relation: "department",
                        },
                        date_from: { string: "From", type: "datetime" },
                        date_to: { string: "To", type: "datetime" },
                        holiday_status_id: {
                            string: "Leave type",
                            type: "many2one",
                            relation: "hr.leave.type",
                        },
                        state: { string: "State", type: "char" },
                        holiday_type: { string: "Holiday Type", type: "char" },
                        number_of_days: { string: "State", type: "integer" },
                        color: { string: "Color", type: "int", relation: "holiday_status_id.color"}
                    }
                },
            },
        };
    },
});


QUnit.test("test employee is passed to has_accrual_allocation", async (assert) => {

    const webClient = await createWebClient({ serverData, async mockRPC(route, args) {
        if (route == '/web/dataset/call_kw/hr.leave/check_access_rights'){
            return true;
        }
        if (route == '/web/dataset/call_kw/hr.leave/get_unusual_days'){
            return {}
        }
        if (route == '/web/dataset/call_kw/hr.employee/get_mandatory_days'){
            return {}
        }
        if (route == '/web/dataset/call_kw/hr.leave.type/get_allocation_data_request'){
            return {}
        }
        if (route == '/web/dataset/call_kw/hr.employee/get_special_days_data'){
            return {
                        "mandatoryDays": [],
                        "bankHolidays": [],
                    }
                }
        if (route == '/web/dataset/call_kw/hr.leave.type/has_accrual_allocation'){
            assert.strictEqual(args.kwargs.context.employee_id, 200, "Should pass the employeeId to has_accrual_allocation");
            return true
        }
    }});

    await doAction(webClient, {
        id: 1,
        res_model: "hr.leave",
        type: "ir.actions.act_window",
        views: [[false, "calendar"]],
        context: { employee_id: [200] },
        domain: [['employee_id', 'in', [200]]],
    });
});
