import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { fields, mountView, models, defineModels } from "@web/../tests/web_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { queryAttribute } from "@odoo/hoot-dom";

class M2oAvatarEmployee extends models.Model {
    _name = "m2o.avatar.employee";
    employee_id = fields.Many2one({ string: "Employee", relation: "hr.employee" });
}

describe.current.tags("desktop");

defineHrHolidaysModels();
defineModels([M2oAvatarEmployee]);

test("avatar card shows leave summary when employee has time off", async () => {
    const pyEnv = await startServer();
    const pierrePid = pyEnv["res.partner"].create({ name: "Pierre" });
    const pierreUid = pyEnv["res.users"].create({ name: "Pierre", partner_id: pierrePid });

    const pierreEid = pyEnv["hr.employee"].create({
        name: "Pierre",
        user_id: pierreUid,
        user_partner_id: pierrePid,
        write_date: "2023-02-13 10:00:00",
        leave_date_to: "2023-02-15",
        avatar_leave_summary: [
            {
                display_name: "Paid Time Off",
                unit: "days",
                leaves_taken: 5,
                remaining_leaves: 15,
                max_leaves: 20,
                requires_allocation: true,
            },
        ],
    });

    pyEnv["m2o.avatar.employee"].create([{ employee_id: pierreEid }]);

    await start();

    await mountView({
        type: "kanban",
        resModel: "m2o.avatar.employee",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="employee_id" widget="many2one_avatar_employee"/>
                </t>
            </templates>
        </kanban>`,
    });

    await contains(".o_m2o_avatar", { count: 1 });
    await contains(".o_field_many2one_avatar_employee img", { count: 1 });
    expect(
        queryAttribute(".o_kanban_record .o_field_many2one_avatar_employee img", "data-src")
    ).toBe(`/web/image/hr.employee/${pierreEid}/avatar_128?unique=1676282400000`);

    await click(".o_kanban_record .o_m2o_avatar > img");
    await contains(".o_avatar_card");
    await contains(".o_avatar_card .o_avatar_card_leave_summary");
    await contains(".o_avatar_card .o_avatar_card_leave_summary .d-flex.small", {
        text: "Paid Time Off: 5 days (15 days)",
    });
});

test("avatar card does not show leave summary when employee has no time off", async () => {
    const pyEnv = await startServer();
    const pierrePid = pyEnv["res.partner"].create({ name: "Pierre" });
    const pierreUid = pyEnv["res.users"].create({ name: "Pierre", partner_id: pierrePid });

    pyEnv["m2o.avatar.employee"].create([
        {
            employee_id: pyEnv["hr.employee"].create({
                name: "Pierre",
                user_id: pierreUid,
                user_partner_id: pierrePid,
                write_date: "2023-02-13 10:00:00",
            }),
        },
    ]);

    await start();

    await mountView({
        type: "kanban",
        resModel: "m2o.avatar.employee",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="employee_id" widget="many2one_avatar_employee"/>
                </t>
            </templates>
        </kanban>`,
    });

    await click(".o_kanban_record .o_m2o_avatar > img");
    await contains(".o_avatar_card");
    await contains(".o_avatar_card .o_avatar_card_leave_summary", { count: 0 });
});
