import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { contains, makeMockServer, mountView } from "@web/../tests/web_test_helpers";
import { contains as mailContains } from "@mail/../tests/mail_test_helpers";
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
        department_id: departmentId,
    });
    const employeeId = env["hr.employee"].create({
        version_id: versionId,
        work_email: "Mario@odoo.pro",
        work_location_type: "office",
        work_phone: "+585555555",
    });
    const userId = env["res.users"].create({
        partner_id: partnerId,
        im_status: "online",
        employee_id: employeeId,
        employee_ids: [employeeId],
    });
    env["hr.employee"].write(employeeId, {
        user_id: userId,
    });
    env["m2x.avatar.user"].create({ user_id: userId });
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
    await mailContains(".o_avatar_card");
    await mailContains(".o_avatar_card span[data-tooltip='Work Location'] .fa-building-o");
    expect(queryAllTexts(".o_card_user_infos > *:not(.o_avatar_card_buttons)")).toEqual([
        "Mario",
        "Management",
        "Mario@odoo.pro",
        "+585555555",
        "Odoo",
    ]);
    await contains(".o_action_manager:eq(0)").click();
    await mailContains(".o_avatar_card", { count: 0 });
});
