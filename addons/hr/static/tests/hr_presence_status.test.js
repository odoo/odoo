import { describe, test, expect } from "@odoo/hoot";
import {
    mountView,
    models,
    defineModels,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
describe.current.tags("desktop");

class HrEmployee extends models.ServerModel {
    _name = "hr.employee";
}
defineMailModels();
defineModels([HrEmployee]);

test("Office Location (online)", async () => {
    expect.assertions(5);
    HrEmployee._records = [
        {
            id: 1,
            name: "Employee test",
            work_location_name: "Office 1",
            work_location_type: "office",
            show_hr_icon_display: true,
            hr_icon_display: "presence_office",
            hr_presence_state: "present",
        },
    ];
    await mountView({
        resModel: "hr.employee",
        type: "form",
        resId: 1,
        arch: `
            <form>
                <field name="hr_icon_display" widget="hr_presence_status"/>
            </form>`,
    });
    expect(".o_employee_availability[data-icon='business']").toHaveCount(1);
    expect(".o_employee_availability[data-icon='home']").toHaveCount(0);
    expect(".o_employee_availability[data-icon='location_on']").toHaveCount(0);
    expect(".o_employee_availability[data-icon='business']").toHaveClass("text-success"); // color == text-success
    expect(".o_employee_availability[data-icon='business'][title='Office 1']").toHaveCount(1);
});

test("Home Location (away)", async () => {
    expect.assertions(5);
    HrEmployee._records = [
        {
            id: 1,
            name: "Employee test",
            work_location_name: "Home",
            work_location_type: "home",
            show_hr_icon_display: true,
            hr_icon_display: "presence_home",
            hr_presence_state: "absent",
        },
    ];
    await mountView({
        resModel: "hr.employee",
        type: "form",
        resId: 1,
        arch: `
            <form>
                <field name="hr_icon_display" widget="hr_presence_status"/>
            </form>`,
    });
    expect(".o_employee_availability[data-icon='home']").toHaveCount(1);
    expect(".o_employee_availability[data-icon='business']").toHaveCount(0);
    expect(".o_employee_availability[data-icon='location_on']").toHaveCount(0);
    expect(".o_employee_availability[data-icon='home']").toHaveClass("o_icon_employee_absent"); // color == text-warning
    expect(".o_employee_availability[data-icon='home'][title='Home']").toHaveCount(1);
});
