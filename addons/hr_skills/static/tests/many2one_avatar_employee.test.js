import { defineHrSkillModels } from "@hr_skills/../tests/hr_skills_test_helpers";
import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { queryAttribute } from "@odoo/hoot-dom";
import { mountView, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineHrSkillModels();

test("many2one_avatar_employee widget in kanban view with skills on avatar card", async () => {
    const pyEnv = await startServer();
    const [java, tigrinya, latin] = pyEnv["hr.skill"].create([
        { name: "Java" },
        { name: "Tigrinya" },
        { name: "Latin" },
    ]);
    const pierrePid = pyEnv["res.partner"].create({ name: "Pierre" });
    const pierreUid = pyEnv["res.users"].create({
        name: "Pierre",
        partner_id: pierrePid,
    });
    const pierreEid = pyEnv["hr.employee"].create({
        name: "Pierre",
        user_id: pierreUid,
        partner_id: pierrePid,
    });
    const [javaForPierre, tigrinyaForPierre, latinForPierre] = pyEnv[
        "hr.employee.skill"
    ].create([
        { employee_id: pierreEid, skill_id: java, valid_from: "2019-01-01" },
        {
            employee_id: pierreEid,
            skill_id: tigrinya,
            valid_from: "2019-01-01",
            valid_to: "2020-01-01",
        },
        {
            employee_id: pierreEid,
            skill_id: latin,
            valid_from: "2018-01-01",
            valid_to: "2019-01-01",
        },
    ]);
    pyEnv["hr.employee"].write([pierreEid], {
        employee_skill_ids: [javaForPierre, tigrinyaForPierre, latinForPierre],
        current_employee_skill_ids: [javaForPierre, latinForPierre],
    });
    pyEnv["m2o.avatar.employee"].create([{ employee_id: pierreEid }]);
    await start();

    onRpc("hr.employee", "get_avatar_card_data", (params) => {
        const resourceIdArray = params.args[0];
        const resourceId = resourceIdArray[0];
        const resources = pyEnv["hr.employee"].read([resourceId]);
        const result = resources.map((resource) => ({
            name: resource.name,
            role_ids: resource.role_ids,
            email: resource.email,
            phone: resource.phone,
            user_id: resource.user_id,
            employee_skill_ids: resource.employee_skill_ids,
            current_employee_skill_ids: resource.current_employee_skill_ids,
        }));
        return result;
    });
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
        queryAttribute(
            ".o_kanban_record .o_field_many2one_avatar_employee img",
            "data-src",
        ),
    ).toBe(`/web/image/hr.employee/${pierreEid}/avatar_128`);
    await click(".o_kanban_record .o_m2o_avatar > img");
    await contains(".o_avatar_card");
    // Tigrinya lapsed in 2020: the card tags what Pierre has, not what he had.
    await contains(".o_avatar_card .o_employee_skills_tags > .o_tag", { count: 1 });
});
