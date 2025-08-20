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
    const jobId = env["hr.job"].create({
        name: "sub manager",
    });
    const workLocationId = env["hr.work.location"].create({
        name: "Odoo",
        location_type: "office",
    });
    const versionId = env["hr.version"].create({
        job_id: jobId,
        work_location_id: workLocationId,
        work_location_type: "office",
        department_id: departmentId,
    });
    const employeeId = env["hr.employee"].create({
        version_id: versionId,
        work_email: "Mario@odoo.pro",
        work_phone: "+585555555",
    });
    const userId = env["res.users"].create({
        partner_id: partnerId,
        im_status: "online",
        employee_id: employeeId,
    });
    env["m2x.avatar.user"].create({ user_id: userId });
    onRpc("/discuss/avatar_card", async (request) => {
        expect.step("/discuss/avatar_card");
        const args = Object.values((await request.json()).params);
        expect(args[0]).toEqual(userId);
        expect(args[1]).toEqual(false);
        expect(args[2]).toEqual([
            "name",
            "email",
            "phone",
            "im_status",
            "share",
            "partner_id",
            "work_phone",
            "work_email",
            "work_location_id",
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
    expect.verifySteps(["/discuss/avatar_card"]);
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_avatar_card span[data-tooltip='Work Location'] .fa-building-o").toHaveCount(1);
    expect(queryAllTexts(".o_card_user_infos > *:not(.o_avatar_card_buttons)")).toEqual([
        "Mario",
        "Management",
        "Mario@odoo.pro",
        "+585555555",
        "Odoo",
    ]);
    await contains(".o_action_manager:eq(0)").click();
    expect(".o_avatar_card").toHaveCount(0);
});
