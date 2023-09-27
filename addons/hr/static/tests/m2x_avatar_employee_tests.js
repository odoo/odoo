/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { dom } from "@web/../tests/legacy/helpers/test_utils";
import { contains } from "@web/../tests/utils";
import { registry } from "@web/core/registry";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";

const serviceRegistry = registry.category("services");

QUnit.module("M2XAvatarEmployee");

QUnit.test("many2one_avatar_employee widget in list view", async function (assert) {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { display_name: "Mario" },
        { display_name: "Luigi" },
    ]);
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
        { name: "Mario", user_id: userId_1, user_partner_id: partnerId_1 },
        { name: "Luigi", user_id: userId_2, user_partner_id: partnerId_2 },
    ]);
    pyEnv["m2x.avatar.employee"].create([
        {
            employee_id: employeeId_1,
            employee_ids: [employeeId_1, employeeId_2],
        },
        { employee_id: employeeId_2 },
        { employee_id: employeeId_1 },
    ]);
    const views = {
        "m2x.avatar.employee,false,list":
            '<tree><field name="employee_id" widget="many2one_avatar_employee"/></tree>',
    };
    const { openView } = await start({
        mockRPC(route, args) {
            if (args.method === "read") {
                assert.step(`read ${args.model} ${args.args[0]}`);
            }
        },
        serverData: { views },
    });
    await openView({
        res_model: "m2x.avatar.employee",
        views: [[false, "list"]],
    });
    assert.strictEqual(
        document.querySelector(".o_data_cell div[name='employee_id']").innerText,
        "Mario"
    );
    assert.strictEqual(
        document.querySelectorAll(".o_data_cell div[name='employee_id']")[1].innerText,
        "Luigi"
    );
    assert.strictEqual(
        document.querySelectorAll(".o_data_cell div[name='employee_id']")[2].innerText,
        "Mario"
    );
    // TODO: avatar card employee
    // click on first employee
    // dom.click(document.querySelector(".o_data_cell .o_m2o_avatar > img"));
    // await contains(".o-mail-ChatWindow");
    // assert.verifySteps([`read hr.employee.public ${employeeId_1}`]);
    // assert.strictEqual(document.querySelector(".o-mail-ChatWindow").textContent, "Mario");

    // // click on second employee
    // dom.click(document.querySelectorAll(".o_data_cell .o_m2o_avatar > img")[1]);
    // await contains(".o-mail-ChatWindow", { count: 2 });
    // assert.verifySteps([`read hr.employee.public ${employeeId_2}`]);
    // assert.strictEqual(
    //     document.querySelectorAll(".o-mail-ChatWindow")[1].textContent,
    //     "Luigi"
    // );

    // // click on third employee (same as first)
    // dom.click(document.querySelectorAll(".o_data_cell .o_m2o_avatar > img")[2]);
    // assert.containsN(
    //     document.body,
    //     ".o-mail-ChatWindow",
    //     2,
    //     "should still have only 2 chat windows because third is the same partner as first"
    // );
    // assert.verifySteps(
    //     [],
    //     "employee should not have been read again because we already know its partner"
    // );
});

QUnit.test("many2one_avatar_employee widget in kanban view", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const employeeId = pyEnv["hr.employee.public"].create({
        user_id: userId,
        user_partner_id: partnerId,
    });
    pyEnv["m2x.avatar.employee"].create({
        employee_id: employeeId,
        employee_ids: [employeeId],
    });
    const views = {
        "m2x.avatar.employee,false,kanban": `<kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="employee_id" widget="many2one_avatar_employee"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "m2x.avatar.employee",
        views: [[false, "kanban"]],
    });
    assert.strictEqual(document.querySelector(".o_kanban_record").innerText.trim(), "");
    await contains(".o_m2o_avatar");
    assert.strictEqual(
        document.querySelector(".o_m2o_avatar > img").getAttribute("data-src"),
        `/web/image/hr.employee.public/${employeeId}/avatar_128`
    );
});

QUnit.test("many2one_avatar_employee with hr group widget in kanban view", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const employeeId = pyEnv["hr.employee.public"].create({
        user_id: userId,
        user_partner_id: partnerId,
    });
    pyEnv["m2x.avatar.employee"].create({
        employee_id: employeeId,
        employee_ids: [employeeId],
    });

    serviceRegistry.add(
        "user",
        makeFakeUserService(() => true),
        { force: true }
    );

    const views = {
        "m2x.avatar.employee,false,kanban": `<kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="employee_id" widget="many2one_avatar_employee"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    };

    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "m2x.avatar.employee",
        views: [[false, "kanban"]],
    });
    assert.strictEqual(document.querySelector(".o_kanban_record").innerText.trim(), "");
    await contains(".o_m2o_avatar");
    assert.strictEqual(
        document.querySelector(".o_m2o_avatar > img").getAttribute("data-src"),
        `/web/image/hr.employee/${employeeId}/avatar_128`
    );
});

QUnit.test("many2one_avatar_employee with relation set in options", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const employeeId = pyEnv["hr.employee.public"].create({
        user_id: userId,
        user_partner_id: partnerId,
    });
    pyEnv["m2x.avatar.employee"].create({
        employee_id: employeeId,
        employee_ids: [employeeId],
    });

    serviceRegistry.add(
        "user",
        makeFakeUserService(() => true),
        { force: true }
    );

    const views = {
        "m2x.avatar.employee,false,kanban": `<kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="employee_id" widget="many2one_avatar_employee" options="{'relation': 'hr.employee.public'}"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    };

    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "m2x.avatar.employee",
        views: [[false, "kanban"]],
    });
    assert.strictEqual(document.querySelector(".o_kanban_record").innerText.trim(), "");
    await contains(".o_m2o_avatar");
    assert.strictEqual(
        document.querySelector(".o_m2o_avatar > img").getAttribute("data-src"),
        `/web/image/hr.employee.public/${employeeId}/avatar_128`
    );
});

QUnit.test(
    "many2one_avatar_employee: click on an employee not associated with a user",
    async function (assert) {
        const pyEnv = await startServer();
        const employeeId = pyEnv["hr.employee.public"].create({ name: "Mario" });
        const avatarId = pyEnv["m2x.avatar.employee"].create({ employee_id: employeeId });
        const views = {
            "m2x.avatar.employee,false,form":
                '<form><field name="employee_id" widget="many2one_avatar_employee"/></form>',
        };
        const { openView } = await start({
            mockRPC(route, args) {
                if (args.method === "web_read") {
                    assert.step(`web_read ${args.model} ${args.args[0]}`);
                    assert.deepEqual(args.kwargs.specification, {
                        display_name: {},
                        employee_id: {
                            fields: {
                                display_name: {},
                            },
                        },
                    });
                }
            },
            serverData: { views },
        });
        await openView({
            res_model: "m2x.avatar.employee",
            res_id: avatarId,
            views: [[false, "form"]],
        });
        await contains(".o_field_widget[name=employee_id] input", { value: "Mario" });
        await dom.click(document.querySelector(".o_m2o_avatar > img"));
        assert.verifySteps([`web_read m2x.avatar.employee ${avatarId}`]);
        // Nothing should happen
    }
);

QUnit.test("many2many_avatar_employee widget in form view", async function (assert) {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([{}, {}]);
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
        { user_id: userId_1, user_partner_id: partnerId_1 },
        { user_id: userId_2, user_partner_id: partnerId_2 },
    ]);
    const avatarId_1 = pyEnv["m2x.avatar.employee"].create({
        employee_ids: [employeeId_1, employeeId_2],
    });
    const views = {
        "m2x.avatar.employee,false,form":
            '<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>',
    };
    const { openView } = await start({
        mockRPC(route, args) {
            if (args.method === "web_read") {
                assert.step(`web_read ${args.model} ${args.args[0]}`);
            }
            if (args.method === "read") {
                assert.step(`read ${args.model} ${args.args[0]}`);
            }
        },
        serverData: { views },
    });
    await openView({
        res_model: "m2x.avatar.employee",
        res_id: avatarId_1,
        views: [[false, "form"]],
    });
    assert.containsN(
        document.body,
        ".o_field_many2many_avatar_employee .o_tag",
        2,
        "should have 2 records"
    );
    assert.strictEqual(
        document
            .querySelector(".o_field_many2many_avatar_employee .o_tag img")
            .getAttribute("data-src"),
        `/web/image/hr.employee.public/${employeeId_1}/avatar_128`
    );

    await dom.click(
        document.querySelector(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")
    );
    await dom.click(
        document.querySelectorAll(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")[1]
    );
    // TODO: avatar card employee
    assert.verifySteps([`web_read m2x.avatar.employee ${avatarId_1}`]);
});

QUnit.test("many2many_avatar_employee with hr group widget in form view", async function (assert) {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([{}, {}]);
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
        { user_id: userId_1, user_partner_id: partnerId_1 },
        { user_id: userId_2, user_partner_id: partnerId_2 },
    ]);
    const avatarId_1 = pyEnv["m2x.avatar.employee"].create({
        employee_ids: [employeeId_1, employeeId_2],
    });
    const views = {
        "m2x.avatar.employee,false,form":
            '<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>',
    };

    // if the user doesn't have access to hr.group_hr_user, the employee field should show the public employee
    serviceRegistry.add(
        "user",
        makeFakeUserService(() => true),
        { force: true }
    );

    const { openView } = await start({
        mockRPC(route, args) {
            if (args.method === "web_read") {
                assert.step(`web_read ${args.model} ${args.args[0]}`);
            }
            if (args.method === "read") {
                assert.step(`read ${args.model} ${args.args[0]}`);
            }
        },
        serverData: { views },
    });
    await openView({
        res_model: "m2x.avatar.employee",
        res_id: avatarId_1,
        views: [[false, "form"]],
    });
    assert.containsN(
        document.body,
        ".o_field_many2many_avatar_employee .o_tag",
        2,
        "should have 2 records"
    );
    assert.strictEqual(
        document
            .querySelector(".o_field_many2many_avatar_employee .o_tag img")
            .getAttribute("data-src"),
        `/web/image/hr.employee/${employeeId_1}/avatar_128`
    );

    await dom.click(
        document.querySelector(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")
    );
    await dom.click(
        document.querySelectorAll(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")[1]
    );
    assert.verifySteps([`web_read m2x.avatar.employee ${avatarId_1}`]);
});

QUnit.test("many2many_avatar_employee widget in list view", async function (assert) {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Yoshi" },
    ]);
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
        { user_id: userId_1, user_partner_id: partnerId_1 },
        { user_id: userId_2, user_partner_id: partnerId_2 },
    ]);
    pyEnv["m2x.avatar.employee"].create({
        employee_ids: [employeeId_1, employeeId_2],
    });
    const views = {
        "m2x.avatar.employee,false,list":
            '<tree><field name="employee_ids" widget="many2many_avatar_employee"/></tree>',
    };
    const { openView } = await start({
        mockRPC(route, args) {
            if (args.method === "read") {
                assert.step(`read ${args.model} ${args.args[0]}`);
            }
        },
        serverData: { views },
    });
    await openView({
        res_model: "m2x.avatar.employee",
        views: [[false, "list"]],
    });
    assert.containsN(
        document.body,
        ".o_data_cell:first .o_field_many2many_avatar_employee > div > span",
        2,
        "should have two avatar"
    );
    // TODO: avatar card employee
    // // click on first employee badge
    // dom.click(document.querySelector(".o_data_cell .o_m2m_avatar"));
    // await contains(".o-mail-ChatWindow");
    // assert.verifySteps([`read hr.employee.public ${employeeId_1}`]);
    // assert.strictEqual(document.querySelector(".o-mail-ChatWindow").textContent, "Mario");

    // // click on second employee
    // dom.click(document.querySelectorAll(".o_data_cell .o_m2m_avatar")[1]);
    // await contains(".o-mail-ChatWindow", { count: 2 });
    // assert.verifySteps([`read hr.employee.public ${employeeId_2}`]);
    // assert.strictEqual(
    //     document.querySelectorAll(".o-mail-ChatWindow")[1].textContent,
    //     "Yoshi"
    // );
});

QUnit.test("many2many_avatar_employee widget in kanban view", async function (assert) {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([{}, {}]);
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
        { user_id: userId_1, user_partner_id: partnerId_1 },
        { user_id: userId_2, user_partner_id: partnerId_2 },
    ]);
    pyEnv["m2x.avatar.employee"].create({
        employee_ids: [employeeId_1, employeeId_2],
    });
    const views = {
        "m2x.avatar.employee,false,kanban": `<kanban>
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
    };
    const { openView } = await start({
        mockRPC(route, args) {
            if (args.method === "read") {
                assert.step(`read ${args.model} ${args.args[0]}`);
            }
        },
        serverData: { views },
    });
    await openView({
        res_model: "m2x.avatar.employee",
        views: [[false, "kanban"]],
    });
    assert.containsN(
        document.body,
        ".o_kanban_record:first .o_field_many2many_avatar_employee img.o_m2m_avatar",
        2,
        "should have 2 avatar images"
    );
    assert.strictEqual(
        document
            .querySelector(".o_kanban_record .o_field_many2many_avatar_employee img.o_m2m_avatar")
            .getAttribute("data-src"),
        `/web/image/hr.employee.public/${employeeId_2}/avatar_128`
    );
    assert.strictEqual(
        document
            .querySelectorAll(
                ".o_kanban_record .o_field_many2many_avatar_employee img.o_m2m_avatar"
            )[1]
            .getAttribute("data-src"),
        `/web/image/hr.employee.public/${employeeId_1}/avatar_128`
    );

    await dom.click(document.querySelectorAll(".o_kanban_record img.o_m2m_avatar")[1]);
    await dom.click(document.querySelectorAll(".o_kanban_record img.o_m2m_avatar")[0]);
    // TODO: avatar card employee
});

QUnit.test(
    "many2many_avatar_employee: click on an employee not associated with a user",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
            {},
            { user_id: userId, user_partner_id: partnerId },
        ]);
        const avatarId = pyEnv["m2x.avatar.employee"].create({
            employee_ids: [employeeId_1, employeeId_2],
        });
        const views = {
            "m2x.avatar.employee,false,form":
                '<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>',
        };
        const { openView } = await start({
            mockRPC(route, args) {
                if (args.method === "read") {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                if (args.method === "web_read") {
                    assert.step(`web_read ${args.model} ${args.args[0]}`);
                }
            },
            serverData: { views },
        });
        await openView({
            res_model: "m2x.avatar.employee",
            res_id: avatarId,
            views: [[false, "form"]],
        });
        await contains(".o_field_many2many_avatar_employee .o_tag", { count: 2 });
        assert.strictEqual(
            document
                .querySelector(".o_field_many2many_avatar_employee .o_tag img")
                .getAttribute("data-src"),
            `/web/image/hr.employee.public/${employeeId_1}/avatar_128`
        );
        await dom.click(
            document.querySelector(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")
        );
        await dom.click(
            document.querySelectorAll(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")[1]
        );
        assert.verifySteps([`web_read m2x.avatar.employee ${employeeId_1}`]);
        // TODO: avtar card employee
    }
);
