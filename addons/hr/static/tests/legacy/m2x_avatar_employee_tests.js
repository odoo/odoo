/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { openFormView, start } from "@mail/../tests/helpers/test_utils";
import { contains } from "@web/../tests/utils";
import { patchUserWithCleanup } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup, click, selectDropdownItem } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { patchAvatarCardPopover } from "@hr/components/avatar_card/avatar_card_popover_patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { getOrigin } from "@web/core/utils/urls";

/* The widgets M2XAVatarEmployee inherits from M2XAvatarUser. Those tests therefore allows
   to test the opening of popover employee cards for both widgets type. If the widgets
   M2XAvatarEmployee are removed in the future, the tests related to opening of popover
   card should be kept as the extension of M2XAvatarUser to support this model is done in
   hr.
 */

QUnit.module("M2XAvatarEmployee", ({ beforeEach }) => {
    beforeEach(() => {
        patchWithCleanup(AvatarCardPopover.prototype, patchAvatarCardPopover);
    });

    QUnit.test("many2one_avatar_employee widget in list view", async function (assert) {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
            { name: "Mario" },
            { name: "Luigi" },
        ]);
        const [userId_1, userId_2] = pyEnv["res.users"].create([
            { partner_id: partnerId_1 },
            { partner_id: partnerId_2 },
        ]);
        const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
            {
                name: "Mario",
                user_id: userId_1,
                user_partner_id: partnerId_1,
                work_email: "Mario@partner.com",
                phone: "+45687468",
            },
            {
                name: "Luigi",
                user_id: userId_2,
                user_partner_id: partnerId_2,
            },
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
                '<list><field name="employee_id" widget="many2one_avatar_employee"/></list>',
        };
        const { openView } = await start({ serverData: { views } });
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

        // click on first employee avatar
        await click(document.querySelector(".o_data_cell .o_m2o_avatar > img"));
        await contains(".o_avatar_card");
        await contains(".o_card_user_infos > span", { text: "Mario" });
        await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
        await contains(".o_card_user_infos > a", { text: "+45687468" });
        assert.strictEqual(
            document.querySelector(".o_avatar_card_buttons button").textContent,
            "Send message"
        );
        await click(document.querySelector(".o_avatar_card_buttons button"));
        await contains(".o-mail-ChatWindow");
        assert.strictEqual(
            document.querySelector(
                ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
            ).textContent,
            "Mario"
        );

        // click on second employee
        await click(document.querySelectorAll(".o_data_cell .o_m2o_avatar > img")[1]);
        await contains(".o_card_user_infos span", { text: "Luigi" });
        await contains(
            ".o_avatar_card",
            { count: 1 },
            "Only one popover employee card should be opened at a time"
        );
        assert.strictEqual(
            document.querySelector(".o_avatar_card_buttons button").textContent,
            "Send message"
        );
        await click(document.querySelector(".o_avatar_card_buttons button"));
        await contains(".o-mail-ChatWindow", { count: 2 });
        assert.strictEqual(
            document.querySelectorAll(
                ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
            )[0].textContent,
            "Luigi"
        );

        // click on third employee (same as first)
        await click(document.querySelectorAll(".o_data_cell .o_m2o_avatar > img")[2]);
        await contains(".o_card_user_infos span", { text: "Mario" });
        await contains(
            ".o_avatar_card",
            { count: 1 },
            "Only one popover employee card should be opened at a time"
        );
        assert.strictEqual(document.querySelector(".o_card_user_infos span").textContent, "Mario");
        await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
        await contains(".o_card_user_infos > a", { text: "+45687468" });
        assert.strictEqual(
            document.querySelector(".o_avatar_card_buttons button").textContent,
            "Send message"
        );
        await click(document.querySelector(".o_avatar_card_buttons button"));
        assert.containsN(
            document.body,
            ".o-mail-ChatWindow",
            2,
            "should still have only 2 chat windows because third is the same partner as first"
        );
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
                    <t t-name="card">
                        <field name="employee_id" widget="many2one_avatar_employee"/>
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
            await start({
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
            await openFormView("m2x.avatar.employee", avatarId);
            await contains(".o_field_widget[name=employee_id] input", { value: "Mario" });
            await click(document.querySelector(".o_m2o_avatar > img"));
            assert.verifySteps([`web_read m2x.avatar.employee ${avatarId}`]);
            // Nothing should happen
        }
    );

    QUnit.test(
        "many2one_avatar_employee with hr group widget in kanban view",
        async function (assert) {
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

            patchUserWithCleanup({ hasGroup: () => Promise.resolve(true) });

            const views = {
                "m2x.avatar.employee,false,kanban": `<kanban>
                    <templates>
                        <t t-name="card">
                            <field name="employee_id" widget="many2one_avatar_employee"/>
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
        }
    );

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

        patchUserWithCleanup({ hasGroup: () => Promise.resolve(true) });

        const views = {
            "m2x.avatar.employee,false,kanban": `<kanban>
                    <templates>
                        <t t-name="card">
                            <field name="employee_id" widget="many2one_avatar_employee" options="{'relation': 'hr.employee.public'}"/>
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

    QUnit.test("many2one_avatar_employee without hr.group_hr_user", async function (assert) {
        assert.expect(2);

        setupViewRegistries();
        patchUserWithCleanup({ hasGroup: (group) => group !== "hr.group_hr_user" });

        await makeView({
            type: "form",
            resModel: "m2x.avatar.employee",
            serverData: {
                models: {
                    "m2x.avatar.employee": {
                        fields: {
                            employee_id: {
                                string: "employee",
                                type: "one2many",
                                relation: "hr.employee",
                            },
                        },
                        records: [],
                    },
                    "hr.employee": {
                        fields: {
                            display_name: { string: "Displayed name", type: "char" },
                        },
                        records: [{ display_name: "babar" }],
                    },
                    "hr.employee.public": {
                        fields: {
                            display_name: { string: "Displayed name", type: "char" },
                        },
                        records: [{ display_name: "babar" }],
                    },
                },
                views: {
                    "hr.employee.public,false,list": `<list><field name="display_name"/></list>`,
                    "hr.employee.public,false,search": `<search></search>`,
                    "hr.employee,false,list": `<list><field name="display_name"/></list>`,
                    "hr.employee,false,search": `<search></search>`,
                },
            },
            arch: `<form><field name="employee_id" widget="many2one_avatar_employee"/></form>`,
            mockRPC: function (_, { model, method }) {
                if (method === "name_search" || method === "web_search_read") {
                    assert.strictEqual(model, "hr.employee.public");
                }
            },
        });
        await selectDropdownItem(document, "employee_id", "Search More...");
    });

    QUnit.test("many2many_avatar_employee widget in form view", async function (assert) {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
            { name: "Mario" },
            { name: "Luigi" },
        ]);
        const [userId_1, userId_2] = pyEnv["res.users"].create([
            { partner_id: partnerId_1 },
            { partner_id: partnerId_2 },
        ]);
        const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
            {
                user_id: userId_1,
                user_partner_id: partnerId_1,
                name: "Mario",
                work_email: "Mario@partner.com",
                phone: "+45687468",
            },
            {
                name: "Luigi",
                user_id: userId_2,
                user_partner_id: partnerId_2,
            },
        ]);
        const avatarId_1 = pyEnv["m2x.avatar.employee"].create({
            employee_ids: [employeeId_1, employeeId_2],
        });
        const views = {
            "m2x.avatar.employee,false,form":
                '<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>',
        };
        await start({
            serverData: { views },
        });
        await openFormView("m2x.avatar.employee", avatarId_1);
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
            `${getOrigin()}/web/image/hr.employee.public/${employeeId_1}/avatar_128`
        );

        // Clicking on first employee's avatar
        await click(
            document.querySelector(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")
        );
        await contains(".o_avatar_card");
        await contains(".o_card_user_infos > span", { text: "Mario" });
        await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
        await contains(".o_card_user_infos > a", { text: "+45687468" });
        assert.strictEqual(
            document.querySelector(".o_avatar_card_buttons button").textContent,
            "Send message"
        );
        click(document.querySelector(".o_avatar_card_buttons button"));
        await contains(".o-mail-ChatWindow");
        assert.strictEqual(
            document.querySelector(
                ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
            ).textContent,
            "Mario"
        );

        // Clicking on second employee's avatar
        await click(
            document.querySelectorAll(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")[1]
        );
        await contains(".o_card_user_infos span", { text: "Luigi" });
        await contains(
            ".o_avatar_card",
            { count: 1 },
            "Only one popover employee card should be opened at a time"
        );
        assert.strictEqual(
            document.querySelector(".o_avatar_card_buttons button").textContent,
            "Send message"
        );
        click(document.querySelector(".o_avatar_card_buttons button"));
        await contains(".o-mail-ChatWindow", { count: 2 });
        assert.strictEqual(
            document.querySelectorAll(
                ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
            )[0].textContent,
            "Luigi"
        );
    });

    QUnit.test(
        "many2many_avatar_employee with hr group widget in form view",
        async function (assert) {
            const pyEnv = await startServer();
            const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([{}, {}]);
            const [userId_1, userId_2] = pyEnv["res.users"].create([
                { partner_id: partnerId_1 },
                { partner_id: partnerId_2 },
            ]);
            const [employeeData_1, employeeData_2] = [
                { user_id: userId_1, user_partner_id: partnerId_1 },
                { user_id: userId_2, user_partner_id: partnerId_2 },
            ];
            // Creating hr.employee and hr.employee.public records with the same id
            pyEnv["hr.employee"].create([{ ...employeeData_1 }, { ...employeeData_2 }]);
            const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
                { ...employeeData_1 },
                { ...employeeData_2 },
            ]);
            const avatarId_1 = pyEnv["m2x.avatar.employee"].create({
                employee_ids: [employeeId_1, employeeId_2],
            });
            const views = {
                "m2x.avatar.employee,false,form":
                    '<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>',
            };

            // Granting all users access to hr.group_hr_user
            // (reminder: if the user doesn't have access to hr.group_hr_user, the employee field should show the public employee, else the hr.employee record)
            patchUserWithCleanup({ hasGroup: () => Promise.resolve(true) });

            await start({
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
            await openFormView("m2x.avatar.employee", avatarId_1);
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
                `${getOrigin()}/web/image/hr.employee/${employeeId_1}/avatar_128`
            );

            await click(
                document.querySelector(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")
            );
            await click(
                document.querySelectorAll(
                    ".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar"
                )[1]
            );
            assert.verifySteps([
                `web_read m2x.avatar.employee ${avatarId_1}`,
                `read hr.employee ${employeeId_1}`,
                `read hr.employee ${employeeId_2}`,
            ]);
        }
    );

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
            {
                name: "Mario",
                user_id: userId_1,
                user_partner_id: partnerId_1,
                phone: "+45687468",
                email: "Mario@partner.com",
            },
            {
                name: "Yoshi",
                user_id: userId_2,
                user_partner_id: partnerId_2,
            },
        ]);
        pyEnv["m2x.avatar.employee"].create({
            employee_ids: [employeeId_1, employeeId_2],
        });
        const views = {
            "m2x.avatar.employee,false,list":
                '<list><field name="employee_ids" widget="many2many_avatar_employee"/></list>',
        };
        const { openView } = await start({
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

        // Clicking on first employee's avatar
        await click(document.querySelector(".o_data_cell .o_m2m_avatar"));
        await contains(".o_avatar_card");
        await contains(".o_card_user_infos > span", { text: "Mario" });
        await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
        await contains(".o_card_user_infos > a", { text: "+45687468" });
        assert.strictEqual(
            document.querySelector(".o_avatar_card_buttons button").textContent,
            "Send message"
        );
        await click(document.querySelector(".o_avatar_card_buttons button"));
        await contains(".o-mail-ChatWindow");
        assert.strictEqual(
            document.querySelector(
                ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
            ).textContent,
            "Mario"
        );

        // Clicking on second employee's avatar
        await click(document.querySelectorAll(".o_data_cell .o_m2m_avatar")[1]);
        await contains(".o_card_user_infos span", { text: "Yoshi" });
        await contains(
            ".o_avatar_card",
            { count: 1 },
            "Only one popover employee card should be opened at a time"
        );
        assert.strictEqual(
            document.querySelector(".o_avatar_card_buttons button").textContent,
            "Send message"
        );
        click(document.querySelector(".o_avatar_card_buttons button"));
        await contains(".o-mail-ChatWindow", { count: 2 });
        assert.strictEqual(
            document.querySelectorAll(
                ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
            )[0].textContent,
            "Yoshi"
        );
    });

    QUnit.test("many2many_avatar_employee widget in kanban view", async function (assert) {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
            { name: "Mario" },
            { name: "Luigi" },
        ]);
        const [userId_1, userId_2] = pyEnv["res.users"].create([
            { partner_id: partnerId_1 },
            { partner_id: partnerId_2 },
        ]);
        const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
            {
                user_id: userId_1,
                user_partner_id: partnerId_1,
                name: "Mario",
                work_email: "Mario@partner.com",
                phone: "+45687468",
            },
            {
                name: "Luigi",
                user_id: userId_2,
                user_partner_id: partnerId_2,
            },
        ]);
        pyEnv["m2x.avatar.employee"].create({
            employee_ids: [employeeId_1, employeeId_2],
        });
        const views = {
            "m2x.avatar.employee,false,kanban": `<kanban>
                <templates>
                    <t t-name="card">
                        <footer>
                            <field name="employee_ids" widget="many2many_avatar_employee"/>
                        </footer>
                    </t>
                </templates>
            </kanban>`,
        };
        const { openView } = await start({
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
                .querySelector(
                    ".o_kanban_record .o_field_many2many_avatar_employee img.o_m2m_avatar"
                )
                .getAttribute("data-src"),
            `${getOrigin()}/web/image/hr.employee.public/${employeeId_2}/avatar_128`
        );
        assert.strictEqual(
            document
                .querySelectorAll(
                    ".o_kanban_record .o_field_many2many_avatar_employee img.o_m2m_avatar"
                )[1]
                .getAttribute("data-src"),
            `${getOrigin()}/web/image/hr.employee.public/${employeeId_1}/avatar_128`
        );

        // Clicking on first employee's avatar
        await click(document.querySelectorAll(".o_kanban_record img.o_m2m_avatar")[1]);
        await contains(".o_avatar_card");
        await contains(".o_card_user_infos > span", { text: "Mario" });
        await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
        await contains(".o_card_user_infos > a", { text: "+45687468" });
        assert.strictEqual(
            document.querySelector(".o_avatar_card_buttons button").textContent,
            "Send message"
        );
        await click(document.querySelector(".o_avatar_card_buttons button"));
        await contains(".o-mail-ChatWindow");
        assert.strictEqual(
            document.querySelector(
                ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
            ).textContent,
            "Mario"
        );

        // Clicking on second employee's avatar
        await click(document.querySelectorAll(".o_kanban_record img.o_m2m_avatar")[0]);
        await contains(".o_card_user_infos span", { text: "Luigi" });
        await contains(
            ".o_avatar_card",
            { count: 1 },
            "Only one popover employee card should be opened at a time"
        );
        assert.strictEqual(
            document.querySelector(".o_avatar_card_buttons button").textContent,
            "Send message"
        );
        await click(document.querySelector(".o_avatar_card_buttons button"));
        await contains(".o-mail-ChatWindow", { count: 2 });
        assert.strictEqual(
            document.querySelectorAll(
                ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
            )[0].textContent,
            "Luigi"
        );
    });

    QUnit.test(
        "many2many_avatar_employee: click on an employee not associated with a user",
        async function (assert) {
            const pyEnv = await startServer();
            const partnerId = pyEnv["res.partner"].create({ name: "Luigi" });
            const userId = pyEnv["res.users"].create({ partner_id: partnerId });
            const [employeeId_1, employeeId_2] = pyEnv["hr.employee.public"].create([
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
            const avatarId = pyEnv["m2x.avatar.employee"].create({
                employee_ids: [employeeId_1, employeeId_2],
            });
            const views = {
                "m2x.avatar.employee,false,form":
                    '<form><field name="employee_ids" widget="many2many_avatar_employee"/></form>',
            };
            await start({ serverData: { views } });
            await openFormView("m2x.avatar.employee", avatarId);
            await contains(".o_field_many2many_avatar_employee .o_tag", { count: 2 });
            assert.strictEqual(
                document
                    .querySelector(".o_field_many2many_avatar_employee .o_tag img")
                    .getAttribute("data-src"),
                `${getOrigin()}/web/image/hr.employee.public/${employeeId_1}/avatar_128`
            );

            // Clicking on first employee's avatar (employee with no user)
            await click(
                document.querySelector(".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar")
            );
            await contains(".o_avatar_card");
            await contains(".o_card_user_infos > span", { text: "Mario" });
            await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
            assert.strictEqual(
                document.querySelector(".o_avatar_card_buttons button").textContent,
                "View Profile",
                'No "Send Message" should be displayed for this employee as it is linked to no user'
            );
            // Clicking on second employee's avatar (employee with user)
            await click(
                document.querySelectorAll(
                    ".o_field_many2many_avatar_employee .o_tag .o_m2m_avatar"
                )[1]
            );
            await contains(".o_card_user_infos span", { text: "Luigi" });
            await contains(
                ".o_avatar_card",
                { count: 1 },
                "Only one popover employee card should be opened at a time"
            );
            assert.strictEqual(
                document.querySelector(".o_avatar_card_buttons button").textContent,
                "Send message"
            );
            await click(document.querySelector(".o_avatar_card_buttons button"));
            await contains(".o-mail-ChatWindow", { count: 1 });
            assert.strictEqual(
                document.querySelector(
                    ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate"
                ).textContent,
                "Luigi"
            );
        }
    );
});
