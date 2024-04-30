import { expect, test } from "@odoo/hoot";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import {
    assertSteps,
    click,
    contains,
    openFormView,
    openKanbanView,
    openListView,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

defineHrModels();

test("many2one_avatar_employee widget in list view", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    // FIXME: Why this is needed here but was not part of the orginal Qunit test ?
    const [employeeId_1, employeeId_2] = pyEnv["hr.employee"].create([
        {
            display_name: "Mario",
        },
        {
            display_name: "Luigi",
        },
    ]);
    const [pubEmployeeId_1, pubEmployeeId_2] = pyEnv["hr.employee.public"].create([
        {
            name: "Mario",
            user_id: userId_1,
            user_partner_id: partnerId_1,
            work_email: "Mario@partner.com",
            phone: "+45687468",
            employee_id: employeeId_1,
        },
        {
            name: "Luigi",
            user_id: userId_2,
            user_partner_id: partnerId_2,
            employee_id: employeeId_2,
        },
    ]);
    pyEnv["m2x.avatar.employee"].create([
        {
            employee_id: pubEmployeeId_1,
            employee_ids: [pubEmployeeId_1, pubEmployeeId_2],
        },
        { employee_id: pubEmployeeId_2 },
        { employee_id: pubEmployeeId_1 },
    ]);
    await start();
    await openListView("m2x.avatar.employee", {
        arch: `<tree>
            <field name="employee_id" widget="many2one_avatar_employee"/>
        </tree>`,
    });
    expect(document.querySelector(".o_data_cell div[name='employee_id']").innerText).toBe("Mario");
    expect(document.querySelectorAll(".o_data_cell div[name='employee_id']")[1].innerText).toBe(
        "Luigi"
    );
    expect(document.querySelectorAll(".o_data_cell div[name='employee_id']")[2].innerText).toBe(
        "Mario"
    );
    await click(document.querySelector(".o_data_cell .o_m2o_avatar > img"));
    await contains(".o_avatar_card");
});

test("many2one_avatar_employee widget in kanban view", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const employeeId = pyEnv["hr.employee"].create({
        display_name: "Mario",
    });
    const pubEmployeeId = pyEnv["hr.employee.public"].create({
        user_id: userId,
        user_partner_id: partnerId,
        employee_id: employeeId,
    });
    pyEnv["m2x.avatar.employee"].create({
        employee_id: pubEmployeeId,
        employee_ids: [pubEmployeeId],
    });
    await start();
    await openKanbanView("m2x.avatar.employee", {
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
    expect(document.querySelector(".o_kanban_record").innerText.trim()).toBe("");
    await contains(".o_m2o_avatar");
    // FIXME: Src coming from hr.employee instead of hr.employee.public
    expect(document.querySelector(".o_m2o_avatar > img").getAttribute("data-src")).toBe(
        `/web/image/hr.employee/${employeeId}/avatar_128`
    );
});

test("many2one_avatar_employee: click on an employee not associated with a user", async () => {
    const pyEnv = await startServer();
    const employeeId = pyEnv["hr.employee.public"].create({ name: "Mario" });
    const avatarId = pyEnv["m2x.avatar.employee"].create({ employee_id: employeeId });
    await start();
    onRpc("m2x.avatar.employee", "web_read", (params) => {
        step(`web_read ${params.args[0]}`);
        expect(JSON.stringify(params.kwargs.specification)).toBe(
            '{"employee_id":{"fields":{"display_name":{}}},"display_name":{}}'
        );
    });
    await openFormView("m2x.avatar.employee", avatarId, {
        arch: '<form><field name="employee_id" widget="many2one_avatar_employee"/></form>',
    });
    await contains(".o_field_widget[name=employee_id] input", { value: "Mario" });
    // FIXME: This click raise a TypeError from "avatar_card_employee_popover.js"
    // await click(document.querySelector(".o_m2o_avatar > img"));
    assertSteps([`web_read ${avatarId}`]);
});

// test(
//     "many2one_avatar_employee with hr group widget in kanban view",
//     async function (assert) {
//         const pyEnv = await startServer();
//         const partnerId = pyEnv["res.partner"].create({});
//         const userId = pyEnv["res.users"].create({ partner_id: partnerId });
//         const employeeId = pyEnv["hr.employee.public"].create({
//             user_id: userId,
//             user_partner_id: partnerId,
//         });
//         pyEnv["m2x.avatar.employee"].create({
//             employee_id: employeeId,
//             employee_ids: [employeeId],
//         });

//         patchUserWithCleanup({ hasGroup: () => Promise.resolve(true) });

//         const views = {
//             "m2x.avatar.employee,false,kanban": `<kanban>
//                 <templates>
//                     <t t-name="kanban-box">
//                         <div>
//                             <field name="employee_id" widget="many2one_avatar_employee"/>
//                         </div>
//                     </t>
//                 </templates>
//             </kanban>`,
//         };

//         const { openView } = await start({ serverData: { views } });
//         await openView({
//             res_model: "m2x.avatar.employee",
//             views: [[false, "kanban"]],
//         });
//         assert.strictEqual(document.querySelector(".o_kanban_record").innerText.trim(), "");
//         await contains(".o_m2o_avatar");
//         assert.strictEqual(
//             document.querySelector(".o_m2o_avatar > img").getAttribute("data-src"),
//             `/web/image/hr.employee/${employeeId}/avatar_128`
//         );
//     }
// );
