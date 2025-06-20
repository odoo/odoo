import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import { start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains, makeMockServer, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { getOrigin } from "@web/core/utils/urls";

describe.current.tags("desktop");
defineHrModels();

test("many2one in list view", async () => {
    const { env } = await makeMockServer();
    const [partnerId_1, partnerId_2] = env["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    const [userId_1, userId_2] = env["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeId_1, employeeId_2] = env["hr.employee.public"].create([
        {
            name: "Mario",
            user_id: userId_1,
            user_partner_id: partnerId_1,
            work_email: "Mario@partner.com",
        },
        {
            name: "Luigi",
            user_id: userId_2,
            user_partner_id: partnerId_2,
        },
    ]);
    env["m2x.avatar.employee"].create([
        {
            employee_id: employeeId_1,
            employee_ids: [employeeId_1, employeeId_2],
        },
        { employee_id: employeeId_2 },
        { employee_id: employeeId_1 },
    ]);
    await start();
    onRpc("has_group", () => false);
    await mountView({
        type: "list",
        resModel: "m2x.avatar.employee",
        arch: `<list><field name="employee_id" widget="many2one_avatar_employee"/></list>`,
    });
    expect(".o_data_cell div[name='employee_id']:eq(0)").toHaveText("Mario");
    expect(".o_data_cell div[name='employee_id']:eq(1)").toHaveText("Luigi");
    expect(".o_data_cell div[name='employee_id']:eq(2)").toHaveText("Mario");
    expect("div[name='employee_id'] a").toHaveCount(0);

    // click on first employee avatar
    await contains(".o_data_cell .o_m2o_avatar > img:eq(0)").click();
    await waitFor(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow");
    await waitFor(".o-mail-ChatWindow-header:contains('Mario')");

    // click on second employee
    await contains(".o_data_cell .o_m2o_avatar > img:eq(1)").click();
    expect(".o_card_user_infos span").toHaveText("Luigi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow-header:contains('Luigi')");
    expect(".o-mail-ChatWindow").toHaveCount(2);

    // click on third employee (same as first)
    await contains(".o_data_cell .o_m2o_avatar > img:eq(2)").click();
    expect(".o_card_user_infos span").toHaveText("Mario");
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_card_user_infos span:eq(0)").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow-header:contains('Mario')");
    expect(".o-mail-ChatWindow").toHaveCount(2);
});

test("many2one in kanban view", async () => {
    const { env } = await makeMockServer();
    const partnerId = env["res.partner"].create({});
    const userId = env["res.users"].create({ partner_id: partnerId });
    const employeeId = env["hr.employee.public"].create({
        user_id: userId,
        user_partner_id: partnerId,
    });
    env["m2x.avatar.employee"].create({
        employee_id: employeeId,
        employee_ids: [employeeId],
    });
    onRpc("has_group", () => false);
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.employee",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="employee_id" widget="many2one_avatar_employee"/>
                </t>
            </templates>
        </kanban>`,
    });
    expect(".o_kanban_record:eq(0)").toHaveText("");
    await waitFor(".o_m2o_avatar");
    expect(".o_m2o_avatar > img:eq(0)").toHaveAttribute(
        "data-src",
        `/web/image/hr.employee.public/${employeeId}/avatar_128`
    );
});

test("many2one: click on an employee not associated with a user", async () => {
    const { env } = await makeMockServer();
    const employeeId = env["hr.employee.public"].create({ name: "Mario" });
    const avatarId = env["m2x.avatar.employee"].create({ employee_id: employeeId });
    onRpc("has_group", () => false);
    await mountView({
        type: "form",
        resModel: "m2x.avatar.employee",
        resId: avatarId,
        arch: `<form><field name="employee_id" widget="many2one_avatar_employee"/></form>`,
    });
    await waitFor(".o_field_widget[name=employee_id] input:value(Mario)");
    await contains(".o_m2o_avatar > img").click();
});

test("many2one with hr group widget in kanban view", async () => {
    const { env } = await makeMockServer();
    const partnerId = env["res.partner"].create({});
    const userId = env["res.users"].create({ partner_id: partnerId });
    const employeeId = env["hr.employee.public"].create({
        user_id: userId,
        user_partner_id: partnerId,
    });
    env["m2x.avatar.employee"].create({
        employee_id: employeeId,
        employee_ids: [employeeId],
    });
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.employee",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="employee_id" widget="many2one_avatar_employee"/>
                </t>
            </templates>
        </kanban>`,
    });
    expect(".o_kanban_record:eq(0)").toHaveText("");
    await waitFor(".o_m2o_avatar");
    expect(".o_m2o_avatar > img:eq(0)").toHaveAttribute(
        "data-src",
        `/web/image/hr.employee/${employeeId}/avatar_128`
    );
});

test("many2one with relation set in options", async () => {
    const { env } = await makeMockServer();
    const partnerId = env["res.partner"].create({});
    const userId = env["res.users"].create({ partner_id: partnerId });
    const employeeId = env["hr.employee.public"].create({
        user_id: userId,
        user_partner_id: partnerId,
    });
    env["m2x.avatar.employee"].create({
        employee_id: employeeId,
        employee_ids: [employeeId],
    });
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.employee",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="employee_id" widget="many2one_avatar_employee" options="{'relation': 'hr.employee.public'}"/>
                </t>
            </templates>
        </kanban>`,
    });
    expect(".o_kanban_record:eq(0)").toHaveText("");
    await waitFor(".o_m2o_avatar");
    expect(".o_m2o_avatar > img:eq(0)").toHaveAttribute(
        "data-src",
        `/web/image/hr.employee.public/${employeeId}/avatar_128`
    );
});

test("many2one without hr.group_hr_user", async () => {
    const { env } = await makeMockServer();
    env["m2x.avatar.employee"].create({});
    env["hr.employee"].create({ name: "babar" });
    env["hr.employee.public"].create({ name: "babar" });
    onRpc("web_name_search", (args) => {
        expect.step("web_name_search");
        expect(args.model).toBe("hr.employee.public");
    });
    onRpc("web_search_read", (args) => {
        expect.step("web_search_read");
        expect(args.model).toBe("hr.employee.public");
    });
    onRpc("has_group", () => false);
    await mountView({
        type: "form",
        resModel: "m2x.avatar.employee",
        arch: `<form><field name="employee_id" widget="many2one_avatar_employee"/></form>`,
    });

    await waitFor(".o-autocomplete--input.o_input");
    await contains(".o-autocomplete--input.o_input").click();
    expect.verifySteps(["web_name_search"]);

    await waitFor(".o_m2o_dropdown_option_search_more");
    await contains(".o_m2o_dropdown_option_search_more").click();
    expect.verifySteps(["web_search_read"]);
});

test("many2one in form view", async () => {
    const { env } = await makeMockServer();
    const [partnerId_1, partnerId_2] = env["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    const [userId_1, userId_2] = env["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeId_1, employeeId_2] = env["hr.employee.public"].create([
        {
            user_id: userId_1,
            user_partner_id: partnerId_1,
            name: "Mario",
            work_email: "Mario@partner.com",
        },
        {
            name: "Luigi",
            user_id: userId_2,
            user_partner_id: partnerId_2,
        },
    ]);
    const avatarId_1 = env["m2x.avatar.employee"].create({
        employee_ids: [employeeId_1, employeeId_2],
    });
    await start();
    onRpc("has_group", () => false);
    await mountView({
        type: "form",
        resId: avatarId_1,
        resModel: "m2x.avatar.employee",
        arch: `<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>`,
    });
    expect(".o_field_many2many_avatar_employee .o_tag").toHaveCount(2);
    expect(".o_field_many2many_avatar_employee .o_tag img:eq(0)").toHaveAttribute(
        "data-src",
        `${getOrigin()}/web/image/hr.employee.public/${employeeId_1}/avatar_128`
    );

    // Clicking on first employee's avatar
    await contains(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar:eq(0)").click();
    await waitFor(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow");
    await waitFor(".o-mail-ChatWindow-header:contains('Mario')");

    // Clicking on second employee's avatar
    await contains(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar:eq(1)").click();
    expect(".o_card_user_infos span").toHaveText("Luigi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow-header:contains('Luigi')");
    expect(".o-mail-ChatWindow").toHaveCount(2);
});

test("many2one with hr group widget in form view", async () => {
    const { env } = await makeMockServer();
    const [partnerId_1, partnerId_2] = env["res.partner"].create([{}, {}]);
    const [userId_1, userId_2] = env["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeData_1, employeeData_2] = [
        { user_id: userId_1, user_partner_id: partnerId_1 },
        { user_id: userId_2, user_partner_id: partnerId_2 },
    ];
    env["hr.employee"].create([{ ...employeeData_1 }, { ...employeeData_2 }]);
    const [employeeId_1, employeeId_2] = env["hr.employee.public"].create([
        { ...employeeData_1 },
        { ...employeeData_2 },
    ]);
    const avatarId_1 = env["m2x.avatar.employee"].create({
        employee_ids: [employeeId_1, employeeId_2],
    });
    expect.step(`read hr.employee ${employeeId_1}`);
    expect.step(`read hr.employee ${employeeId_2}`);
    await mountView({
        type: "form",
        resId: avatarId_1,
        resModel: "m2x.avatar.employee",
        arch: `<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>`,
    });
    expect(".o_field_many2many_avatar_employee .o_tag").toHaveCount(2);
    expect(".o_field_many2many_avatar_employee .o_tag img:eq(0)").toHaveAttribute(
        "data-src",
        `${getOrigin()}/web/image/hr.employee/${employeeId_1}/avatar_128`
    );
    await contains(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar:eq(0)").click();
    await contains(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar:eq(1)").click();
    expect.verifySteps([
        `read hr.employee ${employeeId_1}`,
        `read hr.employee ${employeeId_2}`,
    ]);
});

test("many2one widget in list view", async () => {
    const { env } = await makeMockServer();
    const [partnerId_1, partnerId_2] = env["res.partner"].create([
        { name: "Mario" },
        { name: "Yoshi" },
    ]);
    const [userId_1, userId_2] = env["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeId_1, employeeId_2] = env["hr.employee.public"].create([
        {
            name: "Mario",
            user_id: userId_1,
            user_partner_id: partnerId_1,
            work_email: "Mario@partner.com",
        },
        {
            name: "Yoshi",
            user_id: userId_2,
            user_partner_id: partnerId_2,
        },
    ]);
    env["m2x.avatar.employee"].create({
        employee_ids: [employeeId_1, employeeId_2],
    });
    onRpc("has_group", () => false);
    await start();
    await mountView({
        type: "list",
        resModel: "m2x.avatar.employee",
        arch: `<list><field name="employee_ids" widget="many2many_avatar_employee"/></list>`,
    });
    expect(".o_data_cell:first .o_field_many2many_avatar_employee > div > span").toHaveCount(2);

    // Clicking on first employee's avatar
    await contains(".o_data_cell .o_m2m_avatar:eq(0)").click();
    await waitFor(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow");
    await waitFor(".o-mail-ChatWindow-header:contains('Mario')");

    // Clicking on second employee's avatar
    await contains(".o_data_cell .o_m2m_avatar:eq(1)").click();
    expect(".o_card_user_infos span").toHaveText("Yoshi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow-header:contains('Yoshi')");
});

test("many2many in kanban view", async () => {
    const { env } = await makeMockServer();
    const [partnerId_1, partnerId_2] = env["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    const [userId_1, userId_2] = env["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeId_1, employeeId_2] = env["hr.employee.public"].create([
        {
            user_id: userId_1,
            user_partner_id: partnerId_1,
            name: "Mario",
            work_email: "Mario@partner.com",
        },
        {
            name: "Luigi",
            user_id: userId_2,
            user_partner_id: partnerId_2,
        },
    ]);
    env["m2x.avatar.employee"].create({
        employee_ids: [employeeId_1, employeeId_2],
    });
    onRpc("has_group", () => false);
    await start();
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.employee",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <footer>
                        <field name="employee_ids" widget="many2many_avatar_employee"/>
                    </footer>
                </t>
            </templates>
        </kanban>`,
    });
    expect(
        ".o_kanban_record:first .o_field_many2many_avatar_employee img.o_m2m_avatar"
    ).toHaveCount(2);
    expect(
        ".o_kanban_record .o_field_many2many_avatar_employee img.o_m2m_avatar:eq(0)"
    ).toHaveAttribute(
        "data-src",
        `${getOrigin()}/web/image/hr.employee.public/${employeeId_2}/avatar_128`
    );
    expect(
        ".o_kanban_record .o_field_many2many_avatar_employee img.o_m2m_avatar:eq(1)"
    ).toHaveAttribute(
        "data-src",
        `${getOrigin()}/web/image/hr.employee.public/${employeeId_1}/avatar_128`
    );

    // Clicking on first employee's avatar
    await contains(".o_kanban_record img.o_m2m_avatar:eq(1)").click();
    await waitFor(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow");
    await waitFor(".o-mail-ChatWindow-header:contains('Mario')");

    // Clicking on second employee's avatar
    await contains(".o_kanban_record img.o_m2m_avatar:eq(0)").click();
    expect(".o_card_user_infos span").toHaveText("Luigi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow-header:contains('Luigi')");
    expect(".o-mail-ChatWindow").toHaveCount(2);
});

test("many2many: click on an employee not associated with a user", async () => {
    const { env } = await makeMockServer();
    const partnerId = env["res.partner"].create({ name: "Luigi" });
    const userId = env["res.users"].create({ partner_id: partnerId });
    const [employeeId_1, employeeId_2] = env["hr.employee.public"].create([
        {
            name: "Mario",
            work_email: "Mario@partner.com",
        },
        {
            name: "Luigi",
            user_id: userId,
            user_partner_id: partnerId,
        },
    ]);
    const avatarId = env["m2x.avatar.employee"].create({
        employee_ids: [employeeId_1, employeeId_2],
    });
    onRpc("has_group", () => false);
    await start();
    await mountView({
        type: "form",
        resModel: "m2x.avatar.employee",
        resId: avatarId,
        arch: `<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>`,
    });
    expect(".o_field_many2many_avatar_employee .o_tag").toHaveCount(2);
    expect(".o_field_many2many_avatar_employee .o_tag img:eq(0)").toHaveAttribute(
        "data-src",
        `${getOrigin()}/web/image/hr.employee.public/${employeeId_1}/avatar_128`
    );

    // Clicking on first employee's avatar (employee with no user)
    await contains(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar:eq(0)").click();
    await waitFor(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("View Profile");

    // Clicking on second employee's avatar (employee with user)
    await contains(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar:eq(1)").click();
    expect(".o_card_user_infos span").toHaveText("Luigi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_avatar_card_buttons button:eq(0)").toHaveText("Send message");
    await contains(".o_avatar_card_buttons button:eq(0)").click();
    await waitFor(".o-mail-ChatWindow-header:contains('Luigi')");
    expect(".o-mail-ChatWindow").toHaveCount(1);
});
