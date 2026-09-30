import { test, expect } from "@odoo/hoot";
import { mountView, models, defineModels } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class HrEmployee extends models.ServerModel {
    _name = "hr.employee";
}
defineMailModels();
defineModels([HrEmployee]);

test("Show Time Off before Work Location", async () => {
    HrEmployee._records = [
        {
            id: 1,
            name: "Employee test",
            work_location_name: "Office 1",
            work_location_type: "office",
            show_hr_icon_display: true,
            hr_icon_display: "presence_holiday_absent",
            leave_date_to: "2025-01-06 00:00:00",
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
    expect("small.fa-building").toHaveCount(0);
    expect("small.fa-plane").toBeVisible();
    expect("div.o_field_hr_presence_status>div").toHaveAttribute("title", "On leave, back on Jan 6, 2025");
    expect("div.o_field_hr_presence_status>div").toHaveClass("btn-outline-warning");
});
