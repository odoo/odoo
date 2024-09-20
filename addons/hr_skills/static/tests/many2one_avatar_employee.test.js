import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { mountView } from "@web/../tests/web_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { queryAttribute } from "@odoo/hoot-dom";
import { defineHrSkillModels } from "@hr_skills/../tests/hr_skills_test_helpers";

describe.current.tags("desktop");
defineHrSkillModels();

test("many2one_avatar_employee widget in kanban view with skills on avatar card", async () => {
    const pyEnv = await startServer();
    const [java, tigrinya] = pyEnv["hr.skill"].create([{ name: "Java" }, { name: "Tigrinya" }]);
    const pierrePid = pyEnv["res.partner"].create({ name: "Pierre" });
    const pierreUid = pyEnv["res.users"].create({ name: "Pierre", partner_id: pierrePid });
    const pierreEid = pyEnv["hr.employee"].create({
        name: "Pierre",
        user_id: pierreUid,
        user_partner_id: pierrePid,
    });
    const [javaForPierre, tigrinyaForPierre] = pyEnv["hr.employee.skill"].create([
        { employee_id: pierreEid, skill_id: java },
        { employee_id: pierreEid, skill_id: tigrinya },
    ]);
    pyEnv["hr.employee.public"].create({
        name: "Pierre",
        employee_skill_ids: [javaForPierre, tigrinyaForPierre],
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
    ).toBe(`/web/image/hr.employee/${pierreEid}/avatar_128`);
    await click(".o_kanban_record .o_m2o_avatar");
    await contains(".o_avatar_card");
    await contains(".o_avatar_card .o_employee_skills_tags > .o_tag", { count: 2 });
});
