import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { contains, makeMockServer, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";

describe.current.tags("desktop");
defineHrModels();

test("avatar card preview with hr", async () => {
    const { env } = await makeMockServer();
    const departmentId = env["hr.department"].create({
        name: "Management",
        complete_name: "Management",
    });
    const partnerId = env["res.partner"].create({
        name: "Mario",
        email: "Mario@odoo.test",
        phone: "+7878698799",
    });
    const employeeId = env["hr.employee"].create({
        work_email: "Mario@odoo.pro",
        work_phone: "+585555555",
        job_title: "sub manager",
        department_id: departmentId,
        work_location_name: "Odoo",
        work_location_type: "office",
    });
    const userId = env["res.users"].create({
        partner_id: partnerId,
        im_status: "online",
        employee_id: employeeId,
    });
    env["m2x.avatar.user"].create({ user_id: userId });
    onRpc("res.users", "read", (request) => {
        expect.step("user read");
        expect(request.args[1]).toEqual([
            "name",
            "email",
            "phone",
            "im_status",
            "share",
            "partner_id",
            "work_phone",
            "work_email",
            "work_location_name",
            "work_location_type",
            "job_title",
            "department_id",
            "employee_ids",
        ]);
    });
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.user",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="user_id" widget="many2one_avatar_user"/>
                </t>
            </templates>
        </kanban>`,
    });
    await contains(".o_m2o_avatar > img").click();
    expect.verifySteps(["user read"]);
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_avatar_card span[data-tooltip='Work Location'] .fa-building-o").toHaveCount(1);
    expect(queryAllTexts(".o_card_user_infos > *")).toEqual([
        "Mario",
        "sub manager",
        "Management",
        "Mario@odoo.pro",
        "+585555555",
        "Odoo",
    ]);
    await contains(".o_action_manager:eq(0)").click();
    expect(".o_avatar_card").toHaveCount(0);
});
