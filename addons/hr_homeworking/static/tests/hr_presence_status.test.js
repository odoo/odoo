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
    expect("small.fa-building").toHaveCount(1);
    expect("small.fa-home").toHaveCount(0);
    expect("small.fa-map-marker").toHaveCount(0);
    expect("small").toHaveClass(["fa-building"]);
    expect("div.rounded-pill[title='Office 1']").toHaveCount(1);
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
    expect("small.fa-home").toHaveCount(1);
    expect("small.fa-building").toHaveCount(0);
    expect("small.fa-map-marker").toHaveCount(0);
    expect("small").toHaveClass(["fa-home"]);
    expect("div.rounded-pill[title='Home']").toHaveCount(1);
});
