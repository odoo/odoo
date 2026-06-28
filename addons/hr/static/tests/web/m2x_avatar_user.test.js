import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    makeMockServer,
    mountView,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";
import {
    click as mailClick,
    contains as mailContains,
    start,
} from "@mail/../tests/mail_test_helpers";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import { cookie } from "@web/core/browser/cookie";
import { user } from "@web/core/user";

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
        work_contact_id: partnerId,
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

test("avatar card activates the employee's company before opening the profile", async () => {
    serverState.companies = [
        { id: 1, name: "Company 1", parent_id: false, child_ids: [] },
        { id: 2, name: "Company 2", parent_id: false, child_ids: [] },
    ];
    cookie.set("cids", "1");
    const { env } = await makeMockServer();
    const partnerId = env["res.partner"].create({ name: "Mario" });
    const employeeId = env["hr.employee"].create({
        company_id: 2,
        work_contact_id: partnerId,
        work_email: "mario@odoo.pro",
    });
    const userId = env["res.users"].create({
        partner_id: partnerId,
        employee_id: employeeId,
        employee_ids: [employeeId],
    });
    env["hr.employee"].write(employeeId, { user_id: userId });
    env["m2x.avatar.user"].create({ user_id: userId });
    onRpc("hr.employee", "get_record_default_action", () => {
        expect.step("get_record_default_action");
        return { type: "ir.actions.act_window_close" };
    });
    await start();
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
    // The employee belongs to a non-active (but allowed) company: the plain
    // "View Profile" button is replaced by a dropdown that activates that company.
    await mailContains(".o_avatar_card_buttons button.dropdown-toggle", { text: "View Profile" });
    await mailContains(".o_avatar_card_buttons button", { count: 2 });
    await mailContains(".o_avatar_card_buttons button", { text: "Send message" });
    await contains(".o_avatar_card_buttons button.dropdown-toggle").click();
    await contains(".o-dropdown-item", {
        text: "Open Employee Profile (activates company)",
    }).click();
    expect.verifySteps(["get_record_default_action"]);
});

test("avatar card preview with hr (partner_id field)", async () => {
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
    env["hr.employee"].write(employeeId, {
        work_contact_id: partnerId,
    });
    env["m2x.avatar.user"].create({ partner_id: partnerId });
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.user",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="partner_id" widget="many2one_avatar_user"/>
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

test("avatar card displays the relevant employee info", async () => {
    // "relevant" means active employee and in active company of current user
    const { env } = await makeMockServer();
    const partnerId = env["res.partner"].create({ name: "John" });
    const userId = env["res.users"].create({ partner_id: partnerId });
    const otherCompanyId = env["res.company"].create({ name: "Other Company" });
    const [department1Id, department2Id, department3Id] = env["hr.department"].create([
        { name: "R&D" },
        { name: "Sales" },
        { name: "HR" },
    ]);
    env["hr.employee"].create([
        {
            department_id: department1Id,
            work_contact_id: partnerId,
            company_id: otherCompanyId,
        },
    ]);
    env["m2x.avatar.user"].create({ partner_id: partnerId });
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.user",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="partner_id" widget="many2one_avatar_user"/>
                </t>
            </templates>
        </kanban>`,
    });
    await mailClick(".o_m2o_avatar > img");
    await mailContains(".o_avatar_card");
    await mailContains(".o_card_user_infos > span:contains('R&D')");
    await mailClick(".o_action_manager:eq(0)"); // click away
    await mailContains(".o_avatar_card", { count: 0 });
    env["hr.employee"].create([
        {
            department_id: department2Id,
            work_contact_id: partnerId,
            company_id: user.activeCompany.id,
        },
    ]);
    await mailClick(".o_m2o_avatar > img");
    await mailContains(".o_avatar_card");
    await mailContains(".o_card_user_infos > span:contains('Sales')");
    await mailClick(".o_action_manager:eq(0)"); // click away
    await mailContains(".o_avatar_card", { count: 0 });
    const employee3Id = env["hr.employee"].create([
        {
            department_id: department3Id,
            work_contact_id: partnerId,
            company_id: user.activeCompany.id,
            user_id: userId,
        },
    ]);
    await mailClick(".o_m2o_avatar > img");
    await mailContains(".o_avatar_card");
    await mailContains(".o_card_user_infos > span:contains('HR')");
    await mailClick(".o_action_manager:eq(0)"); // click away
    await mailContains(".o_avatar_card", { count: 0 });
    env["hr.employee"].write(employee3Id, {
        active: false,
    });
    await mailClick(".o_m2o_avatar > img");
    await mailContains(".o_avatar_card");
    await mailContains(".o_card_user_infos > span:contains('Sales')");
    await mailClick(".o_action_manager:eq(0)"); // click away
    await mailContains(".o_avatar_card", { count: 0 });
});
