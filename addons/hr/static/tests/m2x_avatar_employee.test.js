import { start } from "@mail/../tests/mail_test_helpers";
import { contains, mountView, onRpc, makeMockServer } from "@web/../tests/web_test_helpers";
import { getOrigin } from "@web/core/utils/urls";
import { describe, expect, test } from "@odoo/hoot";
import { queryAll, queryAllAttributes, queryOne, queryFirst } from "@odoo/hoot-dom";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";

describe.current.tags("desktop");
defineHrModels();

test("many2one_avatar_employee widget in list view", async () => {
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
        arch: `<tree><field name="employee_id" widget="many2one_avatar_employee"/></tree>`,
    });
    expect(queryFirst(".o_data_cell div[name='employee_id']").innerText).toBe("Mario");
    expect(queryAll(".o_data_cell div[name='employee_id']")[1].innerText).toBe("Luigi");
    expect(queryAll(".o_data_cell div[name='employee_id']")[2].innerText).toBe("Mario");

    // click on first employee avatar
    await contains(queryAll(".o_data_cell .o_m2o_avatar > img")[0]).click();
    await contains(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    await contains(".o-mail-ChatWindow");
    expect(
        queryOne(
            ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
        ).innerText
    ).toBe("Mario");

    // click on second employee
    await contains(queryAll(".o_data_cell .o_m2o_avatar > img")[1]).click();
    expect(".o_card_user_infos span").toHaveText("Luigi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    expect(".o-mail-ChatWindow").toHaveCount(2);
    expect(
        queryAll(
            ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
        )[1].textContent
    ).toBe("Luigi");

    // click on third employee (same as first)
    await contains(queryAll(".o_data_cell .o_m2o_avatar > img")[2]).click();
    expect(".o_card_user_infos span").toHaveText("Mario");
    expect(".o_avatar_card").toHaveCount(1);
    expect(queryOne(".o_card_user_infos span").textContent).toBe("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    expect(".o-mail-ChatWindow").toHaveCount(2);
});

test("many2one_avatar_employee widget in kanban view", async () => {
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
                <t t-name="kanban-box">
                    <div>
                        <field name="employee_id" widget="many2one_avatar_employee"/>
                    </div>
                </t>
            </templates>
        </kanban>`,
    });
    expect(queryFirst(".o_kanban_record").innerText.trim()).toBe("");
    await contains(".o_m2o_avatar");
    expect(queryAllAttributes(".o_m2o_avatar > img", "data-src")[0]).toBe(
        `/web/image/hr.employee.public/${employeeId}/avatar_128`
    );
});

test("many2one_avatar_employee: click on an employee not associated with a user", async () => {
    const { env } = await makeMockServer();
    const employeeId = env["hr.employee.public"].create({ name: "Mario" });
    const avatarId = env["m2x.avatar.employee"].create({ employee_id: employeeId });
    onRpc("web_read", (args) => {
        expect.step(`web_read ${args.model} ${args.args[0]}`);
        expect(args.kwargs.specification).toEqual({
            employee_id: {
                fields: {
                    display_name: {},
                },
            },
            display_name: {},
        });
    });
    onRpc("has_group", () => false);
    await mountView({
        type: "form",
        resModel: "m2x.avatar.employee",
        resId: avatarId,
        arch: `<form><field name="employee_id" widget="many2one_avatar_employee"/></form>`,
    });
    await contains(".o_field_widget[name=employee_id] input", { value: "Mario" });
    await contains(queryFirst(".o_m2o_avatar > img")).click();
    expect.verifySteps([`web_read m2x.avatar.employee ${avatarId}`]);
});

test("many2one_avatar_employee with hr group widget in kanban view", async () => {
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
                <t t-name="kanban-box">
                    <div>
                        <field name="employee_id" widget="many2one_avatar_employee"/>
                    </div>
                </t>
            </templates>
        </kanban>`,
    });
    expect(queryFirst(".o_kanban_record").innerText.trim()).toBe("");
    await contains(".o_m2o_avatar");
    expect(queryAllAttributes(".o_m2o_avatar > img", "data-src")[0]).toBe(
        `/web/image/hr.employee/${employeeId}/avatar_128`
    );
});

test("many2one_avatar_employee with relation set in options", async () => {
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
                <t t-name="kanban-box">
                    <div>
                        <field name="employee_id" widget="many2one_avatar_employee" options="{'relation': 'hr.employee.public'}"/>
                    </div>
                </t>
            </templates>
        </kanban>`,
    });
    expect(queryFirst(".o_kanban_record").innerText.trim()).toBe("");
    await contains(".o_m2o_avatar");
    expect(queryAllAttributes(".o_m2o_avatar > img", "data-src")[0]).toBe(
        `/web/image/hr.employee.public/${employeeId}/avatar_128`
    );
});

test("many2one_avatar_employee without hr.group_hr_user", async () => {
    const { env } = await makeMockServer();
    env["m2x.avatar.employee"].create({});
    env["hr.employee"].create({ name: "babar" });
    env["hr.employee.public"].create({ name: "babar" });
    onRpc("name_search", (args) => {
        expect(args.model).toBe("hr.employee.public");
    });
    onRpc("web_search_read", (args) => {
        expect(args.model).toBe("hr.employee.public");
    });
    onRpc("has_group", () => false);
    await mountView({
        type: "form",
        resModel: "m2x.avatar.employee",
        arch: `<form><field name="employee_id" widget="many2one_avatar_employee"/></form>`,
    });

    await contains(".o-autocomplete--input.o_input");
    await contains(".o-autocomplete--input.o_input").click();
    await contains(".o_m2o_dropdown_option_search_more");
    await contains(".o_m2o_dropdown_option_search_more").click();
});

test("many2many_avatar_employee widget in form view", async () => {
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
    expect(queryAllAttributes(".o_field_many2many_avatar_employee .o_tag img", "data-src")[0]).toBe(
        `${getOrigin()}/web/image/hr.employee.public/${employeeId_1}/avatar_128`
    );

    // Clicking on first employee's avatar
    await contains(queryFirst(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")).click();
    await contains(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    await contains(".o-mail-ChatWindow");
    expect(
        queryFirst(
            ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
        ).textContent
    ).toBe("Mario");

    // Clicking on second employee's avatar
    await contains(queryAll(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")[1]).click();
    expect(".o_card_user_infos span").toHaveText("Luigi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    expect(".o-mail-ChatWindow").toHaveCount(2);
    expect(
        queryAll(
            ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
        )[1].textContent
    ).toBe("Luigi");
});

test("many2many_avatar_employee with hr group widget in form view", async () => {
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
    onRpc("web_read", (args) => {
        expect.step(`web_read ${args.model} ${args.args[0]}`);
    });
    onRpc("read", (args) => {
        expect.step(`read ${args.model} ${args.args[0]}`);
    });
    await mountView({
        type: "form",
        resId: avatarId_1,
        resModel: "m2x.avatar.employee",
        arch: `<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>`,
    });
    await contains(".o_field_many2many_avatar_employee .o_tag", { count: 2 });
    expect(queryAllAttributes(".o_field_many2many_avatar_employee .o_tag img", "data-src")[0]).toBe(
        `${getOrigin()}/web/image/hr.employee/${employeeId_1}/avatar_128`
    );
    await contains(queryFirst(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")).click();
    await contains(queryAll(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")[1]).click();
    expect.verifySteps([
        `web_read m2x.avatar.employee ${avatarId_1}`,
        `read hr.employee ${employeeId_1}`,
        `read hr.employee ${employeeId_2}`,
    ]);
});

test("many2many_avatar_employee widget in list view", async () => {
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
    await start();
    await mountView({
        type: "list",
        resModel: "m2x.avatar.employee",
        arch: `<tree><field name="employee_ids" widget="many2many_avatar_employee"/></tree>`,
    });
    expect(".o_data_cell:first .o_field_many2many_avatar_employee > div > span").toHaveCount(2);

    // Clicking on first employee's avatar
    await contains(queryFirst(".o_data_cell .o_m2m_avatar")).click();
    await contains(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    await contains(".o-mail-ChatWindow");
    expect(
        queryFirst(
            ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
        ).textContent
    ).toBe("Mario");

    // Clicking on second employee's avatar
    await contains(queryAll(".o_data_cell .o_m2m_avatar")[1]).click();
    expect(".o_card_user_infos span").toHaveText("Yoshi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    expect(".o-mail-ChatWindow").toHaveCount(2);
    expect(
        queryAll(
            ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
        )[1].textContent
    ).toBe("Yoshi");
});

test("many2many_avatar_employee widget in kanban view", async () => {
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
                <t t-name="kanban-box">
                    <div>
                        <div class="oe_kanban_footer">
                            <div class="o_kanban_record_bottom">
                                <div class="oe_kanban_bottom_right">
                                    <field name="employee_ids" widget="many2many_avatar_employee"/>
                                </div>
                            </div>
                        </div>
                    </div>
                </t>
            </templates>
        </kanban>`,
    });
    expect(
        ".o_kanban_record:first .o_field_many2many_avatar_employee img.o_m2m_avatar"
    ).toHaveCount(2);
    expect(
        queryAllAttributes(
            ".o_kanban_record .o_field_many2many_avatar_employee img.o_m2m_avatar",
            "data-src"
        )[0]
    ).toBe(`${getOrigin()}/web/image/hr.employee.public/${employeeId_2}/avatar_128`);
    expect(
        queryAllAttributes(
            ".o_kanban_record .o_field_many2many_avatar_employee img.o_m2m_avatar",
            "data-src"
        )[1]
    ).toBe(`${getOrigin()}/web/image/hr.employee.public/${employeeId_1}/avatar_128`);

    // Clicking on first employee's avatar
    await contains(queryAll(".o_kanban_record img.o_m2m_avatar")[1]).click();
    await contains(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    await contains(".o-mail-ChatWindow");
    expect(
        queryFirst(
            ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
        ).textContent
    ).toBe("Mario");

    // Clicking on second employee's avatar
    await contains(queryFirst(".o_kanban_record img.o_m2m_avatar")).click();
    expect(".o_card_user_infos span").toHaveText("Luigi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    expect(".o-mail-ChatWindow").toHaveCount(2);
    expect(
        queryAll(
            ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
        )[1].textContent
    ).toBe("Luigi");
});

test("many2many_avatar_employee: click on an employee not associated with a user", async () => {
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
    expect(queryAllAttributes(".o_field_many2many_avatar_employee .o_tag img", "data-src")[0]).toBe(
        `${getOrigin()}/web/image/hr.employee.public/${employeeId_1}/avatar_128`
    );

    // Clicking on first employee's avatar (employee with no user)
    await contains(queryFirst(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")).click();
    await contains(".o_avatar_card");
    expect(".o_card_user_infos > span").toHaveText("Mario");
    expect(".o_card_user_infos > a").toHaveText("Mario@partner.com");
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe(" View profile ");

    // Clicking on second employee's avatar (employee with user)
    await contains(queryAll(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")[1]).click();
    expect(".o_card_user_infos span").toHaveText("Luigi");
    expect(".o_avatar_card").toHaveCount(1);
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await contains(queryFirst(".o_avatar_card_buttons button")).click();
    expect(".o-mail-ChatWindow").toHaveCount(1);
    expect(
        queryFirst(
            ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
        ).textContent
    ).toBe("Luigi");
});
