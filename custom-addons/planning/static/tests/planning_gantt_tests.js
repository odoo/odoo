/* @odoo-module */

import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import {
    click,
    clickSave,
    editInput,
    getFixture,
    patchDate,
    patchTimeZone,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { contains } from "@web/../tests/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

import {
    clickCell,
    editPill,
    getGridContent,
    hoverGridCell,
    SELECTORS,
} from "@web_gantt/../tests/helpers";

const serviceRegistry = registry.category("services");

async function ganttResourceWorkIntervalRPC(_, args) {
    if (args.method === "gantt_resource_work_interval") {
        return [
            {
                1: [
                    ["2022-10-10 06:00:00", "2022-10-10 10:00:00"], //Monday    4h
                    ["2022-10-11 06:00:00", "2022-10-11 10:00:00"], //Tuesday   5h
                    ["2022-10-11 11:00:00", "2022-10-11 12:00:00"],
                    ["2022-10-12 06:00:00", "2022-10-12 10:00:00"], //Wednesday 6h
                    ["2022-10-12 11:00:00", "2022-10-12 13:00:00"],
                    ["2022-10-13 06:00:00", "2022-10-13 10:00:00"], //Thursday  7h
                    ["2022-10-13 11:00:00", "2022-10-13 14:00:00"],
                    ["2022-10-14 06:00:00", "2022-10-14 10:00:00"], //Friday    8h
                    ["2022-10-14 11:00:00", "2022-10-14 15:00:00"],
                ],
                false: [
                    ["2022-10-10 06:00:00", "2022-10-10 10:00:00"],
                    ["2022-10-10 11:00:00", "2022-10-10 15:00:00"],
                    ["2022-10-11 06:00:00", "2022-10-11 10:00:00"],
                    ["2022-10-11 11:00:00", "2022-10-11 15:00:00"],
                    ["2022-10-12 06:00:00", "2022-10-12 10:00:00"],
                    ["2022-10-12 11:00:00", "2022-10-12 15:00:00"],
                    ["2022-10-13 06:00:00", "2022-10-13 10:00:00"],
                    ["2022-10-13 11:00:00", "2022-10-13 15:00:00"],
                    ["2022-10-14 06:00:00", "2022-10-14 10:00:00"],
                    ["2022-10-14 11:00:00", "2022-10-14 15:00:00"],
                ],
            },
            {false: true},
        ];
    }
}

let serverData;
let target;
QUnit.module("Views", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                task: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        start_datetime: { string: "Start Date", type: "datetime" },
                        end_datetime: { string: "Stop Date", type: "datetime" },
                        time: { string: "Time", type: "float" },
                        resource_id: {
                            string: "Assigned to",
                            type: "many2one",
                            relation: "resource.resource",
                        },
                        department_id: {
                            string: "Department",
                            type: "many2one",
                            relation: "department",
                        },
                        role_id: {
                            string: "Role",
                            type: "many2one",
                            relation: "role",
                        },
                        active: { string: "active", type: "boolean", default: true },
                    },
                    records: [],
                },
                "resource.resource": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [],
                },
                department: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [],
                },
                role: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [],
                },
            },
            views: {
                "foo,false,gantt": `<gantt/>`,
                "foo,false,search": `<search/>`,
            },
        };
        setupViewRegistries();
        target = getFixture();
    });

    QUnit.module("PlanningGanttView");

    QUnit.test("empty gantt view: send schedule", async function () {
        patchDate(2018, 11, 20, 8, 0, 0);
        serverData.models.task.records = [];
        await makeView({
            type: "gantt",
            resModel: "task",
            serverData,
            arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime"/>`,
            domain: Domain.FALSE.toList(),
            groupBy: ["resource_id"],
        });
        await click(target.querySelector(".o_gantt_button_send_all.btn-primary"));
        await contains(".o_notification.border-danger", {
            text: "The shifts have already been published, or there are no shifts to publish.",
        });
    });

    QUnit.test("empty gantt view with sample data: send schedule", async function (assert) {
        patchDate(2018, 11, 20, 8, 0, 0);
        serverData.models.task.records = [];
        await makeView({
            type: "gantt",
            resModel: "task",
            serverData,
            arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" sample="1"/>`,
            domain: Domain.FALSE.toList(),
            groupBy: ["resource_id"],
        });
        assert.hasClass(target.querySelector(".o_gantt_view .o_content"), "o_view_sample_data");
        assert.ok(target.querySelectorAll(".o_gantt_row_headers .o_gantt_row_header").length >= 2);
        await click(target.querySelector(".o_gantt_button_send_all.btn-primary"));
        await contains(".o_notification.border-danger", {
            text: "The shifts have already been published, or there are no shifts to publish.",
        });
    });

    QUnit.test('add record in empty gantt with sample="1"', async function (assert) {
        assert.expect(6);

        serverData.models.task.records = [];
        serverData.views = {
            "task,false,form": `
                <form>
                    <field name="name"/>
                    <field name="start_datetime"/>
                    <field name="end_datetime"/>
                    <field name="resource_id"/>
                </form>`,
        };

        await makeView({
            type: "gantt",
            resModel: "task",
            serverData,
            arch: '<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" sample="1" plan="false"/>',
            groupBy: ["resource_id"],
            mockRPC: ganttResourceWorkIntervalRPC,
        });

        assert.hasClass(target.querySelector(".o_gantt_view .o_content"), "o_view_sample_data");
        assert.ok(target.querySelectorAll(".o_gantt_row_headers .o_gantt_row_header").length >= 2);
        const firstRow = target.querySelector(".o_gantt_row_headers .o_gantt_row_header");
        assert.strictEqual(firstRow.innerText, "Open Shifts");
        assert.doesNotHaveClass(firstRow, "o_sample_data_disabled");

        await hoverGridCell(1, 1);
        await clickCell(1, 1);

        await editInput(target, ".modal .o_form_view .o_field_widget[name=name] input", "new task");
        await clickSave(target.querySelector(".modal"));

        assert.doesNotHaveClass(
            target.querySelector(".o_gantt_view .o_content"),
            "o_view_sample_data"
        );
        assert.containsOnce(target, ".o_gantt_pill_wrapper");
    });

    QUnit.test("open a dialog to add a new task", async function (assert) {
        assert.expect(4);

        patchTimeZone(0);

        serverData.views = {
            "task,false,form": `
                <form>
                    <field name="name"/>
                    <field name="start_datetime"/>
                    <field name="end_datetime"/>
                '</form>
            `,
        };

        const now = luxon.DateTime.now();

        await makeView({
            type: "gantt",
            resModel: "task",
            serverData,
            arch: '<gantt js_class="planning_gantt" default_scale="day" date_start="start_datetime" date_stop="end_datetime"/>',
            mockRPC(_, args) {
                if (args.method === "onchange") {
                    assert.strictEqual(
                        args.kwargs.context.default_end_datetime,
                        now.startOf("day").toFormat("yyyy-MM-dd 23:59:59")
                    );
                }
            },
        });

        await click(target, ".d-xl-inline-flex .o_gantt_button_add.btn-primary");
        // check that the dialog is opened with prefilled fields
        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=start_datetime] .o_input").value,
            now.toFormat("MM/dd/yyyy 00:00:00")
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=end_datetime] .o_input").value,
            now.toFormat("MM/dd/yyyy 23:59:59")
        );
    });

    QUnit.test(
        "gantt view collapse and expand empty rows in multi groupby",
        async function (assert) {
            assert.expect(7);

            await makeView({
                type: "gantt",
                resModel: "task",
                serverData,
                arch: '<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime"/>',
                groupBy: ["department_id", "role_id", "resource_id"],
            });

            const { rows } = getGridContent();
            assert.deepEqual(
                rows.map((r) => r.title),
                ["Open Shifts", "Undefined Role", "Open Shifts"]
            );

            function getRow(index) {
                return target.querySelectorAll(".o_gantt_row_headers > .o_gantt_row_header")[index];
            }

            await click(getRow(0));
            assert.doesNotHaveClass(getRow(0), "o_group_open");
            await click(getRow(0));
            assert.hasClass(getRow(0), "o_group_open");
            assert.strictEqual(getRow(2).innerText, "Open Shifts");
            await click(getRow(1));
            assert.doesNotHaveClass(getRow(1), "o_group_open");
            await click(getRow(1));
            assert.hasClass(getRow(1), "o_group_open");
            assert.strictEqual(getRow(2).innerText, "Open Shifts");
        }
    );

    function _getCreateViewArgsForGanttViewTotalsTests() {
        patchDate(2022, 9, 13, 0, 0, 0);
        serverData.models["resource.resource"].records.push({ id: 1, name: "Resource 1" });
        serverData.models.task.fields.allocated_percentage = {
            string: "Allocated Percentage",
            type: "float",
        };
        serverData.models.task.records.push({
            id: 1,
            name: "test",
            start_datetime: "2022-10-09 00:00:00",
            end_datetime: "2022-10-16 22:00:00",
            resource_id: 1,
            allocated_percentage: 50,
        });
        return {
            type: "gantt",
            resModel: "task",
            serverData,
            arch: `
                <gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" total_row="1" default_scale="week"
                        precision="{'day': 'hour:full', 'week': 'day:full', 'month': 'day:full', 'year': 'day:full'}">
                    <field name="allocated_percentage"/>
                    <field name="resource_id"/>
                    <field name="name"/>
                </gantt>
            `,
            mockRPC: ganttResourceWorkIntervalRPC,
        };
    }

    QUnit.test(
        "gantt view totals height is taking unavailability into account instead of pills count",
        async function (assert) {
            await makeView(_getCreateViewArgsForGanttViewTotalsTests());

            // 2022-10-09 and 2022-10-15 are days off => no pill has to be found in first and last columns
            assert.deepEqual(
                [...target.querySelectorAll(".o_gantt_row_total .o_gantt_pill_wrapper")].map(
                    (el) => el.style.gridColumn.split(" / ")[0]
                ),
                ["2", "3", "4", "5", "6"]
            );

            // Max of allocated hours = 4:00 (50% * 8:00)
            assert.deepEqual(
                [...target.querySelectorAll(".o_gantt_row_total .o_gantt_pill")].map(
                    (el) => el.style.height
                ),
                [
                    "45%", // => 2:00 = 50% of 4:00 => 0.5 * 90% = 45%
                    "56.25%", // => 2:30 = 62.5% of 4:00 => 0.625 * 90% = 56.25%
                    "67.5%", // => 3:00 = 75% of 4:00 => 0.75 * 90% = 67.5%
                    "78.75%", // => 3:30 = 87.5% of 4:00 => 0.85 * 90% = 78.75%
                    "90%", // => 4:00 = 100% of 4:00 => 1 * 90% = 90%
                ]
            );
        }
    );

    QUnit.test(
        "gantt view totals are taking unavailability into account for the total display",
        async function (assert) {
            await makeView(_getCreateViewArgsForGanttViewTotalsTests());
            assert.deepEqual(
                [...target.querySelectorAll(".o_gantt_row_total .o_gantt_pill")].map(
                    (el) => el.innerText
                ),
                ["02:00", "02:30", "03:00", "03:30", "04:00"]
            );
        }
    );

    QUnit.test(
        "gantt view totals are taking unavailability into account according to scale",
        async function (assert) {
            const createViewArgs = _getCreateViewArgsForGanttViewTotalsTests();
            createViewArgs.arch = createViewArgs.arch.replace(
                'default_scale="week"',
                'default_scale="year"'
            );

            await makeView(createViewArgs);

            assert.containsOnce(target, ".o_gantt_cells .o_gantt_pill");
            assert.containsOnce(target, ".o_gantt_row_total .o_gantt_pill");
            assert.strictEqual(
                target.querySelector(".o_gantt_row_total .o_gantt_pill").innerText,
                "15:00"
            );
        }
    );

    QUnit.test(
        "reload data after having unlink a record in planning_form",
        async function (assert) {
            serverData.views = {
                "task,false,form": `
                <form js_class="planning_form">
                    <field name="name"/>
                    <field name="start_datetime"/>
                    <field name="end_datetime"/>
                    <field name="resource_id"/>
                    <footer class="d-flex flex-wrap">
                        <button name="unlink" type="object" icon="fa-trash" title="Remove" class="btn-secondary" close="1"/>
                    </footer>
                </form>`,
            };
            await makeView(_getCreateViewArgsForGanttViewTotalsTests());

            assert.containsOnce(target, ".o_gantt_cells .o_gantt_pill");

            await editPill("test");
            await click(target, ".modal footer button[name=unlink]"); // click on trash icon
            await click(target, ".o_dialog:nth-child(2) .modal footer button:nth-child(1)"); // click on "Ok" in confirmation dialog

            assert.containsNone(target, ".o_gantt_cells .o_gantt_pill");
        }
    );

    QUnit.test("progress bar has the correct unit", async (assert) => {
        const makeViewArgs = _getCreateViewArgsForGanttViewTotalsTests();
        assert.expect(9);
        await makeView({
            ...makeViewArgs,
            arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" progress_bar="resource_id"/>`,
            groupBy: ["resource_id"],
            async mockRPC(_, { args, method, model }) {
                if (method === "gantt_progress_bar") {
                    assert.strictEqual(model, "task");
                    assert.deepEqual(args[0], ["resource_id"]);
                    assert.deepEqual(args[1], { resource_id: [1] });
                    return {
                        resource_id: {
                            1: { value: 100, max_value: 100 },
                        },
                    };
                }
                return makeViewArgs.mockRPC(...arguments);
            },
        });
        assert.containsOnce(target, SELECTORS.progressBar);
        assert.containsOnce(target, SELECTORS.progressBarBackground);
        assert.strictEqual(
            target.querySelector(SELECTORS.progressBarBackground).style.width,
            "100%"
        );

        assert.containsNone(target, SELECTORS.progressBarForeground);
        await hoverGridCell(2, 1);
        assert.containsOnce(target, SELECTORS.progressBarForeground);
        assert.deepEqual(
            target.querySelector(SELECTORS.progressBarForeground).textContent,
            "100h / 100h"
        );
    });

    QUnit.test("progress bar has the correct percentage", async (assert) => {
        const makeViewArgs = _getCreateViewArgsForGanttViewTotalsTests();
        assert.expect(10);
        await makeView({
            ...makeViewArgs,
            arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" progress_bar="resource_id"/>`,
            groupBy: ["resource_id"],
            async mockRPC(_, { args, method, model }) {
                if (method === "gantt_progress_bar") {
                    assert.strictEqual(model, "task");
                    assert.deepEqual(args[0], ["resource_id"]);
                    assert.deepEqual(args[1], { resource_id: [1] });
                    return {
                        resource_id: {
                            1: { value: 10, max_value: 40 },
                        },
                    };
                }
                return makeViewArgs.mockRPC(...arguments);
            },
        });
        assert.containsOnce(target, SELECTORS.progressBar);
        assert.containsOnce(target, SELECTORS.progressBarBackground);
        assert.strictEqual(
            target.querySelector(SELECTORS.progressBarBackground).style.width,
            "25%"
        );

        assert.containsNone(target, SELECTORS.progressBarForeground);
        await hoverGridCell(2, 1);
        assert.containsOnce(target, SELECTORS.progressBarForeground);
        assert.strictEqual(
            target.querySelector(SELECTORS.progressBarForeground).textContent,
            "10h / 40h"
        );
        assert.strictEqual(
            target.querySelector(SELECTORS.progressBar + " > span > .ms-1").textContent,
            "(25%)"
        );
    });

    QUnit.test("total computes correctly for open shifts", async (assert) => {
        // For open shifts and shifts with flexible resource, the total should be computed
        // based on the shifts' duration, each maxed to the calendar's hours per day.
        // Not based on the intersection of the shifts and the calendar.
        const createViewArgs = _getCreateViewArgsForGanttViewTotalsTests();
        serverData.models.task.fields.allocated_hours = {
            string: "Allocated Hours",
            type: "float",
        };
        serverData.models.task.records[0] = {
            id: 1,
            name: "test",
            start_datetime: "2022-10-10 04:00:00",
            end_datetime: "2022-10-10 12:00:00",
            resource_id: false,
            allocated_hours: 8,
            allocated_percentage: 100,
        };
        createViewArgs.arch = createViewArgs.arch.replace(
            'default_scale="week"',
            'default_scale="week" default_group_by="resource_id"'
        ).replace(
            '<field name="allocated_percentage"/>',
            '<field name="allocated_percentage"/><field name="allocated_hours"/>',
        );
        await makeView(createViewArgs);
        assert.strictEqual(
            target.querySelector(SELECTORS.rowTotal).textContent,
            "08:00"
        );
    });

    QUnit.test("Test split tool in gantt view", async function (assert) {
        patchDate(2022, 9, 13, 0, 0, 0);
        patchWithCleanup(luxon.Settings, {
            defaultZone: luxon.IANAZone.create("UTC"),
        });
        serverData.models.task.records.push(
            {
                id: 1,
                name: "test",
                start_datetime: "2022-10-08 16:00:00",
                end_datetime: "2022-10-09 00:00:00",
                resource_id: 1,
            },
            {
                id: 2,
                name: "test",
                start_datetime: "2022-10-10 12:00:00",
                end_datetime: "2022-10-11 12:00:00",
                resource_id: 1,
            }
        );
        const hasGroup = () => true;
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

        await makeView({
            type: "gantt",
            resModel: "task",
            serverData,
            arch: `
                <gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" scales="week" default_scale="week"/>
            `,
            mockRPC: ganttResourceWorkIntervalRPC,
        });
        assert.containsN(target, ".o_gantt_pill", 2, "2 pills should be in the gantt view.");
        assert.containsOnce(
            target,
            ".o_gantt_pill_split_tool",
            "The split tool should only be available on the second pill."
        );
        const splitToolEl = target.querySelector(".o_gantt_pill_split_tool");
        assert.strictEqual(
            splitToolEl.dataset.splitToolPillId,
            "__pill__2_0",
            "The split tool should be positioned on the pill 2 after the first column of the pill since the pill is on 2 columns."
        );
    });
});
