/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { getFixture, patchDate } from "@web/../tests/helpers/utils";
import { start } from "@mail/../tests/helpers/test_utils";

let serverData;
let target;
QUnit.module("Views", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        const [resPartnerId1, resPartnerId2, resPartnerId3] = pyEnv["res.partner"].create([
            { display_name: "Mario" },
            { display_name: "Luigi" },
            { display_name: "Yoshi" },
        ]);
        const [resUsersId1, resUsersId2, resUsersId3] = pyEnv["res.users"].create([
            { partner_id: resPartnerId1 },
            { partner_id: resPartnerId2 },
            { partner_id: resPartnerId3 },
        ]);
        const [hrEmployeePublicId1, hrEmployeePublicId2, hrEmployeePublicId3] = pyEnv[
            "hr.employee.public"
        ].create([
            { name: "Mario", user_id: resUsersId1, user_partner_id: resPartnerId1 },
            { name: "Luigi", user_id: resUsersId2, user_partner_id: resPartnerId2 },
            { name: "Yoshi", user_id: resUsersId3, user_partner_id: resPartnerId3 },
        ]);
        pyEnv.mockServer.models.tasks = {
            fields: {
                id: { string: "ID", type: "integer" },
                display_name: { string: "Name", type: "char" },
                start: { string: "Start Date", type: "datetime" },
                stop: { string: "Stop Date", type: "datetime" },
                employee_id: {
                    string: "Employee",
                    type: "many2one",
                    relation: "hr.employee.public",
                },
                foo: { string: "Foo", type: "char" },
            },
            records: [
                {
                    id: 1,
                    display_name: "Task 1",
                    start: "2018-11-30 18:30:00",
                    stop: "2018-12-31 18:29:59",
                    employee_id: hrEmployeePublicId1,
                    foo: "Foo 1",
                },
                {
                    id: 2,
                    display_name: "Task 2",
                    start: "2018-12-17 11:30:00",
                    stop: "2018-12-22 06:29:59",
                    employee_id: hrEmployeePublicId2,
                    foo: "Foo 2",
                },
                {
                    id: 3,
                    display_name: "Task 3",
                    start: "2018-12-27 06:30:00",
                    stop: "2019-01-03 06:29:59",
                    employee_id: hrEmployeePublicId3,
                    foo: "Foo 1",
                },
                {
                    id: 4,
                    display_name: "Task 4",
                    start: "2018-12-19 18:30:00",
                    stop: "2018-12-20 06:29:59",
                    employee_id: hrEmployeePublicId1,
                    foo: "Foo 3",
                },
            ],
        };

        serverData = {
            views: {
                "tasks,false,search": `<search/>`,
                "tasks,false,gantt":
                    '<gantt js_class="hr_gantt" date_start="start" date_stop="stop" />',
            },
        };
        patchDate(2018, 11, 20, 8, 0, 0);
        target = getFixture();
    });

    QUnit.module("HrGanttView");

    QUnit.test("hr gantt view not grouped", async (assert) => {
        const { openView } = await start({ serverData });
        await openView({
            res_model: "tasks",
            views: [[false, "gantt"]],
            context: { group_by: [] },
        });
        assert.containsNone(target, ".o-mail-Avatar");
    });

    QUnit.test("hr gantt view grouped by employee only", async (assert) => {
        const { openView } = await start({ serverData });
        await openView({
            res_model: "tasks",
            views: [[false, "gantt"]],
            context: { group_by: ["employee_id"] },
        });
        assert.containsN(target, ".o_gantt_row_title .o-mail-Avatar", 3);
    });

    QUnit.test("hr gantt view grouped by employee > foo", async (assert) => {
        const { openView } = await start({ serverData });
        await openView({
            res_model: "tasks",
            views: [[false, "gantt"]],
            context: { group_by: ["employee_id", "foo"] },
        });
        assert.containsN(
            target,
            ".o_gantt_row_header.o_gantt_group .o_gantt_row_title .o-mail-Avatar",
            3
        );
    });

    QUnit.test("hr gantt view grouped by foo > employee", async (assert) => {
        const { openView } = await start({ serverData });
        await openView({
            res_model: "tasks",
            views: [[false, "gantt"]],
            context: { group_by: ["foo", "employee_id"] },
        });
        assert.containsN(
            target,
            ".o_gantt_row_header:not(.o_gantt_group) .o_gantt_row_title .o-mail-Avatar",
            4
        );
    });
});
