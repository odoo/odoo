import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, queryAll, queryAllTexts, queryFirst, waitFor } from "@odoo/hoot-dom";
import { animationFrame, mockDate, mockTimeZone } from "@odoo/hoot-mock";
import {
    clickSave,
    contains,
    defineActions,
    getFacetTexts,
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {
    CLASSES,
    clickCell,
    dragPill,
    editPill,
    getGridContent,
    getPillWrapper,
    hoverGridCell,
    mountGanttView,
    resizePill,
    SELECTORS,
    selectRange,
} from "@web_gantt/../tests/web_gantt_test_helpers";

import { Domain } from "@web/core/domain";
import { redirect } from "@web/core/utils/urls";
import { WebClient } from "@web/webclient/webclient";

import {
    definePlanningModels,
    HrEmployee,
    PlanningSlot,
    ResourceResource,
} from "./planning_mock_models";

describe.current.tags("desktop");

definePlanningModels();

defineActions([
    {
        id: 1,
        name: "Planning slot Action 1",
        res_model: "planning.slot",
        type: "ir.actions.act_window",
        mobile_view_mode: "gantt",
        views: [[false, "gantt"]],
    },
]);

const getProgressBars = () => ({
    resource_id: {
        1: {
            value: 16.4,
            max_value: 40,
            employee_id: 1,
            is_material_resource: true,
            display_popover_material_resource: false,
        },
    },
});

async function reccureneceDeletionTemplate(mode) {
    onRpc("planning.slot", "action_address_recurrency", ({ args }) => {
        expect.step(`Recurency Delete in mode ${args[1]}`);
        return true;
    });

    const ganttViewProps = _getCreateViewArgsForGanttViewTotalsTests();
    ganttViewProps.groupBy = ["resource_id"];

    PlanningSlot._records[0].repeat = true;
    await mountGanttView(ganttViewProps);

    expect(".o_gantt_pill:not(.o_gantt_consolidated_pill)").toHaveCount(1);

    click(".o_gantt_pill");
    await animationFrame();

    click("button:contains('Delete')");
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    expect(".modal-title").toHaveText("Delete Recurring Shift");
    await animationFrame();
    click(`input[id="${mode}"]`);
    await animationFrame();

    click(".o_dialog button:contains(Delete Recurring Shift)");
    await animationFrame();
    expect.verifySteps([`Recurency Delete in mode ${mode}`]);
}

async function ganttResourceWorkIntervalRPC() {
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
        { false: true },
    ];
}

function _getCreateViewArgsForGanttViewTotalsTests() {
    mockDate("2022-10-13 00:00:00", +1);
    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);
    ResourceResource._records = [{ id: 1, name: "Resource 1" }];
    PlanningSlot._records.push({
        id: 1,
        name: "test",
        start_datetime: "2022-10-09 00:00:00",
        end_datetime: "2022-10-16 22:00:00",
        resource_id: 1,
        allocated_percentage: 50,
    });
    return {
        resModel: "planning.slot",
        arch: `
            <gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" total_row="1" default_scale="week"
                    precision="{'day': 'hour:full', 'week': 'day:full', 'month': 'day:full', 'year': 'day:full'}">
                <field name="allocated_percentage"/>
                <field name="resource_id"/>
                <field name="name"/>
                <field name="repeat"/>
            </gantt>
        `,
    };
}

beforeEach(() => {
    ResourceResource._records = [{ id: 1, name: "Resource 1", employee_id: 1 }];
    HrEmployee._records = [{ id: 1, name: "Employee 1" }];
    PlanningSlot._views = {
        form: `<form>
                    <field name="start_datetime"/>
                    <field name="end_datetime"/>
                </form>`,
        list: `<list><field name="name"/></list>`,
    };
    onRpc("has_group", () => true);
});

test("empty gantt view: send schedule", async function () {
    expect.assertions(2);

    mockService("notification", {
        add: (message, options) => {
            expect(message).toBe(
                "The shifts have already been published, or there are no shifts to publish."
            );
            expect(options).toEqual({ type: "danger" });
        },
    });

    await mountGanttView({
        resModel: "planning.slot",
        arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime"/>`,
        domain: Domain.FALSE.toList(),
        groupBy: ["resource_id"],
    });

    await click(".o_gantt_button_send_all.btn-primary");
    await animationFrame();
});

test("empty gantt view with sample data: send schedule", async function () {
    expect.assertions(4);

    mockDate("2018-12-20 07:00:00");
    mockService("notification", {
        add: (message, options) => {
            expect(message).toBe(
                "The shifts have already been published, or there are no shifts to publish."
            );
            expect(options).toEqual({ type: "danger" });
        },
    });

    await mountGanttView({
        resModel: "planning.slot",
        arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" sample="1"/>`,
        domain: Domain.FALSE.toList(),
        groupBy: ["resource_id"],
    });
    expect(".o_gantt_view .o_content").toHaveClass("o_view_sample_data");
    expect(queryAll(".o_gantt_row_headers .o_gantt_row_header").length).toBeGreaterThan(2);

    await click(".o_gantt_button_send_all.btn-primary");
    await animationFrame();
});

test('add record in empty gantt with sample="1"', async function () {
    expect.assertions(6);

    PlanningSlot._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="start_datetime"/>
                <field name="end_datetime"/>
                <field name="resource_id"/>
            </form>
        `,
    };

    mockDate("2018-12-10 07:00:00");
    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);

    await mountGanttView({
        resModel: "planning.slot",
        arch: '<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" sample="1" plan="false"/>',
        groupBy: ["resource_id"],
    });

    expect(".o_gantt_view .o_content").toHaveClass("o_view_sample_data");
    expect(queryAll(".o_gantt_row_headers .o_gantt_row_header").length).toBeGreaterThan(2);
    expect(".o_gantt_row_headers .o_gantt_row_header:first").toHaveText("Open Shifts");
    expect(".o_gantt_row_headers .o_gantt_row_header:first").not.toHaveClass(
        "o_sample_data_disabled"
    );

    await clickCell("01 December 2018", "Open Shifts");
    await contains(".modal .o_form_view .o_field_widget[name=name] input").edit("new shift");
    await clickSave();
    expect(".o_gantt_view .o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_gantt_pill_wrapper").toHaveCount(1);
});

test("open a dialog to add a new shift", async function () {
    expect.assertions(5);

    PlanningSlot._views = {
        form: `
        <form>
        <field name="name"/>
        <field name="start_datetime"/>
        <field name="end_datetime"/>
        '</form>
        `,
    };

    mockTimeZone(0);
    const now = luxon.DateTime.now();
    onRpc("onchange", ({ kwargs }) => {
        expect(kwargs.context.default_end_datetime).toBe(
            now.plus({ day: 1 }).startOf("day").toFormat("yyyy-MM-dd 00:00:00")
        );
    });

    await mountGanttView({
        resModel: "planning.slot",
        arch: '<gantt js_class="planning_gantt" default_scale="day" date_start="start_datetime" date_stop="end_datetime"/>',
    });
    expect(".modal").toHaveCount(0);

    await click(".o_gantt_button_add.btn-primary");
    await animationFrame();

    expect(".modal").toHaveCount(1);
    expect(".o_field_widget[name=start_datetime] .o_input").toHaveValue(
        now.toFormat("MM/dd/yyyy 00:00:00")
    );
    expect(".o_field_widget[name=end_datetime] .o_input").toHaveValue(
        now.plus({ day: 1 }).toFormat("MM/dd/yyyy 00:00:00")
    );
});

test("gantt view collapse and expand empty rows in multi groupby", async function () {
    expect.assertions(7);

    await mountGanttView({
        resModel: "planning.slot",
        arch: '<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime"/>',
        groupBy: ["department_id", "role_id", "resource_id"],
    });

    const { rows } = getGridContent();
    expect(rows.map((r) => r.title)).toEqual(["Open Shifts", "Undefined Role", "Open Shifts"]);

    function getRow(index) {
        return queryAll(".o_gantt_row_headers > .o_gantt_row_header")[index];
    }

    await click(getRow(0));
    await animationFrame();
    expect(getRow(0)).not.toHaveClass("o_group_open");

    await click(getRow(0));
    await animationFrame();
    expect(getRow(0)).toHaveClass("o_group_open");
    expect(getRow(2)).toHaveText("Open Shifts");

    await click(getRow(1));
    await animationFrame();
    expect(getRow(1)).not.toHaveClass("o_group_open");

    await click(getRow(1));
    await animationFrame();
    expect(getRow(1)).toHaveClass("o_group_open");
    expect(getRow(2)).toHaveText("Open Shifts");
});

test("gantt view totals height is taking unavailability into account instead of pills count", async function () {
    await mountGanttView(_getCreateViewArgsForGanttViewTotalsTests());

    // 2022-10-09 and 2022-10-15 are days off => no pill has to be found in first and last columns
    expect(
        queryAll(".o_gantt_row_total .o_gantt_pill_wrapper").map(
            (el) => el.style.gridColumn.split(" / ")[0]
        )
    ).toEqual(["c2", "c3", "c4", "c5", "c6"], {
        message:
            "2022-10-09 and 2022-10-15 are days off => no pill has to be found in first and last columns",
    });

    // Max of allocated hours = 4:00 (50% * 8:00)
    expect(queryAll(".o_gantt_row_total .o_gantt_pill").map((el) => el.style.height)).toEqual([
        "45%", // => 2:00 = 50% of 4:00 => 0.5 * 90% = 45%
        "56.25%", // => 2:30 = 62.5% of 4:00 => 0.625 * 90% = 56.25%
        "67.5%", // => 3:00 = 75% of 4:00 => 0.75 * 90% = 67.5%
        "78.75%", // => 3:30 = 87.5% of 4:00 => 0.85 * 90% = 78.75%
        "90%", // => 4:00 = 100% of 4:00 => 1 * 90% = 90%
    ]);
});

test("gantt view totals are taking unavailability into account for the total display", async function () {
    await mountGanttView(_getCreateViewArgsForGanttViewTotalsTests());
    expect(queryAllTexts(".o_gantt_row_total .o_gantt_pill")).toEqual([
        "02:00",
        "02:30",
        "03:00",
        "03:30",
        "04:00",
    ]);
});

test("gantt view totals are taking unavailability into account according to scale", async function () {
    const createViewArgs = _getCreateViewArgsForGanttViewTotalsTests();
    createViewArgs.arch = createViewArgs.arch.replace(
        'default_scale="week"',
        'default_scale="year"'
    );

    await mountGanttView(createViewArgs);

    expect(".o_gantt_cells .o_gantt_pill").toHaveCount(1);
    expect(".o_gantt_row_total .o_gantt_pill").toHaveCount(1);
    expect(".o_gantt_row_total .o_gantt_pill").toHaveText("15:00");
});

test("reload data after having unlink a record in planning_form", async function () {
    PlanningSlot._views = {
        form: `
                <form js_class="planning_form">
                    <field name="name"/>
                    <field name="start_datetime"/>
                    <field name="end_datetime"/>
                    <field name="resource_id"/>
                    <footer class="d-flex flex-wrap">
                        <button name="unlink" type="object" icon="fa-trash" title="Remove" class="btn-secondary" close="1"/>
                    </footer>
                </form>
            `,
    };
    await mountGanttView(_getCreateViewArgsForGanttViewTotalsTests());

    expect(".o_gantt_cells .o_gantt_pill").toHaveCount(1);

    await editPill("test");
    await click(".modal footer button[name=unlink]"); // click on trash icon
    await animationFrame();
    await click(".o-overlay-item:nth-child(2) .modal footer button:nth-child(1)"); // click on "Ok" in confirmation dialog
    await animationFrame();

    expect(".o_gantt_cells .o_gantt_pill").toHaveCount(0);
});

test("progress bar has the correct unit", async () => {
    const makeViewArgs = _getCreateViewArgsForGanttViewTotalsTests();
    onRpc("get_gantt_data", ({ kwargs, parent }) => {
        const result = parent();
        expect(kwargs.progress_bar_fields).toEqual(["resource_id"]);
        result.progress_bars = getProgressBars();
        return result;
    });

    await mountGanttView({
        ...makeViewArgs,
        arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" progress_bar="resource_id"/>`,
        groupBy: ["resource_id"],
    });
    expect(SELECTORS.progressBar).toHaveCount(1);
    expect(SELECTORS.progressBarBackground).toHaveCount(1);
    expect(queryFirst(SELECTORS.progressBarBackground).style.width).toBe("41%");
    expect(SELECTORS.progressBarForeground).toHaveCount(0);

    await hoverGridCell("02 October 2022", "Resource 1");
    expect(SELECTORS.progressBarForeground).toHaveCount(1);
    expect(SELECTORS.progressBarForeground).toHaveText("16h24 / 40h");
});

test("total computes correctly for open shifts", async () => {
    // For open shifts and shifts with flexible resource, the total should be computed
    // based on the shifts' duration, each maxed to the calendar's hours per day.
    // Not based on the intersection of the shifts and the calendar.
    const createViewArgs = _getCreateViewArgsForGanttViewTotalsTests();
    PlanningSlot._records[0] = {
        id: 1,
        name: "test",
        start_datetime: "2022-10-10 04:00:00",
        end_datetime: "2022-10-10 12:00:00",
        resource_id: false,
        allocated_hours: 8,
        allocated_percentage: 100,
    };
    createViewArgs.arch = createViewArgs.arch
        .replace('default_scale="week"', 'default_scale="week" default_group_by="resource_id"')
        .replace(
            '<field name="allocated_percentage"/>',
            '<field name="allocated_percentage"/><field name="allocated_hours"/>'
        );
    await mountGanttView(createViewArgs);
    expect(queryAll(SELECTORS.rowTotal)[1]).toHaveText("08:00");
});

test("the grouped gantt view is coloured correctly and the occupancy percentage is correctly displayed", async () => {
    mockDate("2022-10-10 00:00:00", +1);

    PlanningSlot._records = [
        {
            id: 1,
            name: "underplanned test slot",
            start_datetime: "2022-10-11 08:00:00",
            end_datetime: "2022-10-11 10:00:00",
            resource_id: 1,
            employee_id: 1,
            allocated_percentage: 100,
        },
        {
            id: 2,
            name: "perfect test slot",
            start_datetime: "2022-10-12 06:00:00",
            end_datetime: "2022-10-12 13:00:00",
            resource_id: 1,
            employee_id: 1,
            allocated_percentage: 100,
        },
        {
            id: 3,
            name: "overplanned test slot",
            start_datetime: "2022-10-13 06:00:00",
            end_datetime: "2022-10-13 16:00:00",
            resource_id: 1,
            employee_id: 1,
            allocated_percentage: 120,
        },
    ];

    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);
    onRpc("get_gantt_data", ({ parent }) => {
        const result = parent();
        result.progress_bars = getProgressBars();
        return result;
    });

    await mountGanttView({
        resModel: "planning.slot",
        arch: `
            <gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" total_row="1" default_scale="week"
                precision="{'day': 'hour:full', 'week': 'day:full', 'month': 'day:full', 'year': 'day:full'}" display_unavailability="1" progress_bar="resource_id"
            >
                <field name="allocated_percentage"/>
                <field name="resource_id"/>
                <field name="employee_id"/>
                <field name="name"/>
            </gantt>
        `,
        groupBy: ["resource_id", "name"],
    });

    const groupPillHeaders = queryAll(".o_gantt_group_pill");
    expect(groupPillHeaders.length).toBe(3);
    // Tuesday
    expect(groupPillHeaders[0].firstChild).toHaveClass("bg-warning border-warning", {
        message: "The grouped pill should be orange because the resource is under planned",
    });
    expect(groupPillHeaders[0].lastChild).toHaveText("02:00 (40%)", {
        message:
            "The grouped pill occupancy percentage should be 40% because a shift of 2 hours was allocated and we expect 5 working hours on Tuesday",
    });
    // Wednesday
    expect(groupPillHeaders[1].firstChild).toHaveClass("bg-success border-success", {
        message: "The grouped pill should be green because the resource is perfectly planned",
    });
    expect(groupPillHeaders[1].lastChild).toHaveText("06:00 (100%)", {
        message:
            "The grouped pill occupancy percentage should be 100% because a shift of 6 hours was allocated and we expect 6 working hours on Wednesday",
    });
    // Thursday
    expect(groupPillHeaders[2].firstChild).toHaveClass("bg-danger border-danger", {
        message: "The grouped pill should be red because the resource is over planned",
    });
    expect(groupPillHeaders[2].lastChild).toHaveText("08:25 (120%)", {
        message:
            "The grouped pill occupancy percentage should be 120% because a shift of 8:25 hours was allocated and we expect 7 working hours on Thursday",
    });
});

test("Gantt Planning : pill name should not display allocated hours if allocated_percentage is 100%", async () => {
    mockDate("2022-10-13 00:00:00", +1);
    PlanningSlot._records = [
        {
            id: 1,
            name: "Shift 1",
            start_datetime: "2022-10-09 08:30:00",
            end_datetime: "2022-10-09 17:30:00", // span only one day
            allocated_hours: 4,
            allocated_percentage: 50,
        },
        {
            id: 2,
            name: "Shift 2",
            start_datetime: "2022-10-09 08:30:00",
            end_datetime: "2022-10-09 17:30:00", // span only one day
            allocated_hours: 8,
            allocated_percentage: 100,
        },
    ];

    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);

    await mountGanttView({
        resModel: "planning.slot",
        arch: `
                <gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" default_scale="week" pill_label="True">
                    <field name="allocated_hours"/>
                    <field name="allocated_percentage"/>
                </gantt>
            `,
        groupBy: ["resource_id"],
    });
    expect(queryAllTexts(".o_gantt_pill")).toEqual([
        "9:30 AM - 6:30 PM (4h) - Shift 1",
        "9:30 AM - 6:30 PM - Shift 2",
    ]);
});

test("Resize or Drag-Drop should open recurrence update wizard", async () => {
    mockDate("2022-10-10 00:00:00", +1);

    ResourceResource._records[0].resource_type = "user";

    PlanningSlot._records.push({
        name: "Shift With Repeat",
        start_datetime: "2022-10-11 08:00:00",
        end_datetime: "2022-10-11 10:00:00",
        resource_id: 1,
        employee_id: 1,
        allocated_percentage: 100,
        repeat: true,
    });

    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);

    await mountGanttView({
        resModel: "planning.slot",
        arch: `
            <gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" total_row="1" default_scale="month"
                precision="{'day': 'hour:full', 'week': 'day:full', 'month': 'day:full', 'year': 'day:full'}" display_unavailability="1" progress_bar="resource_id"
            >
                <field name="allocated_percentage"/>
                <field name="resource_id"/>
                <field name="employee_id"/>
                <field name="name"/>
                <field name="repeat"/>
            </gantt>
        `,
        groupBy: ["resource_id", "name"],
    });

    expect(getPillWrapper("Shift With Repeat")).toHaveClass(CLASSES.draggable);
    expect(getGridContent().rows[3]).toEqual({
        pills: [
            {
                title: "Shift With Repeat",
                level: 0,
                colSpan: "11 October 2022 -> 11 October 2022",
            },
        ],
        title: "Shift With Repeat",
    });

    // move a pill in the next cell (+1 day)
    const { drop } = await dragPill("Shift With Repeat");
    await drop({ row: "Resource 1", column: "12 October 2022" });
    // click on the confirm button
    await click(".modal .btn-primary");
    await animationFrame();
    expect(getGridContent().rows[3]).toEqual({
        pills: [
            {
                title: "Shift With Repeat",
                level: 0,
                colSpan: "12 October 2022 -> 12 October 2022",
            },
        ],
        title: "Shift With Repeat",
    });

    // resize a pill in the next cell (+1 day)
    await resizePill(getPillWrapper("Shift With Repeat"), "end", 1);
    // click on the confirm button
    await click(".modal .btn-primary");
    await animationFrame();
    expect(getGridContent().rows[3]).toEqual({
        pills: [
            {
                title: "Shift With Repeat",
                level: 0,
                colSpan: "12 October 2022 -> 13 October 2022",
            },
        ],
        title: "Shift With Repeat",
    });
});

test("Test split tool in gantt view", async function () {
    mockDate("2022-10-13 00:00:00", +1);
    patchWithCleanup(luxon.Settings, {
        defaultZone: luxon.IANAZone.create("UTC"),
    });
    PlanningSlot._records = [
        {
            id: 1,
            name: "test",
            start_datetime: "2022-10-08 16:00:00",
            end_datetime: "2022-10-09 01:00:00",
            resource_id: 1,
        },
        {
            id: 2,
            name: "test",
            start_datetime: "2022-10-10 12:00:00",
            end_datetime: "2022-10-11 12:00:00",
            resource_id: 1,
        },
    ];

    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);

    await mountGanttView({
        resModel: "planning.slot",
        arch: `
            <gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" scales="week" default_scale="week"/>
        `,
    });
    expect(".o_gantt_pill").toHaveCount(2);
    expect(".o_gantt_pill_split_tool").toHaveCount(1, {
        message: "The split tool should only be available on the second pill.",
    });
    expect(queryFirst(".o_gantt_pill_split_tool").dataset.splitToolPillId).toBe("__pill__2_0", {
        message:
            "The split tool should be positioned on the pill 2 after the first column of the pill since the pill is on 2 columns.",
    });
});

test("Test highlight shifts added by executed action", async function () {
    mockDate("2022-10-05 00:00:00", +1);
    PlanningSlot._records = [
        {
            id: 1,
            name: "test",
            start_datetime: "2022-09-30 16:00:00",
            end_datetime: "2022-09-30 18:00:00",
            resource_id: 1,
        },
        {
            id: 2,
            name: "test",
            start_datetime: "2022-10-05 08:00:00",
            end_datetime: "2022-10-05 12:00:00",
            resource_id: false,
        },
    ];

    onRpc("action_copy_previous_week", function () {
        if (this.env["planning.slot"].length === 2) {
            const newSlotId = this.env["planning.slot"].create({
                name: "shift 3",
                start_datetime: "2022-10-07 16:00:00",
                end_datetime: "2022-10-07 18:00:00",
                resource_id: 1,
            });
            return [[newSlotId], [1]];
        }
        return false;
    });
    onRpc("auto_plan_ids", function () {
        this.env["planning.slot"].write([2], { resource_id: 1 });
        return { open_shift_assigned: [2] };
    });
    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);

    await mountGanttView({
        resModel: "planning.slot",
        arch: `
            <gantt
                js_class="planning_gantt"
                date_start="start_datetime"
                date_stop="end_datetime"
                default_group_by="resource_id"
                default_range="week"
                default_scale="week"
                scales="week,month"
            />
        `,
        searchViewArch: `<search>
                <filter name="shift_planned" invisible="1" string="Shifts Planned" context="{'highlight_planned': 1}"/>
            </search>`,
    });

    await click(
        ".o_control_panel_main_buttons .o_gantt_buttons_container button > i.fa-caret-down"
    );
    await animationFrame();

    expect(".o_gantt_button_copy_previous_week").toHaveCount(1, {
        message: "1 copy button should be in the gantt view.",
    });
    expect(".o_gantt_button_auto_plan").toHaveCount(1, {
        message: "1 copy button should be in the gantt view.",
    });
    expect(".o_gantt_pill").toHaveCount(1, { message: "1 pill should be in the gantt view." });
    let { rows } = getGridContent();
    expect(rows.map((r) => r.title)).toEqual(["Open Shifts"]);

    await click(".o_popover.dropdown-menu .o_gantt_button_copy_previous_week");
    await animationFrame();

    expect(".o_notification .bg-success").toHaveCount(1, {
        message: "The notification should be a success notification.",
    });
    expect(".o_notification button .fa-undo").toHaveCount(1, {
        message: "The notification should have an undo button.",
    });
    expect(getFacetTexts()).toEqual(["Shifts Planned"], {
        message: "Shifts Planned facet should be active.",
    });
    expect(".o_gantt_pill").toHaveCount(2, { message: "2 pills should be in the gantt view." });
    rows = getGridContent().rows;
    expect(rows.map((r) => r.title)).toEqual(["Open Shifts", "Resource 1"]);

    await click(
        ".o_control_panel_main_buttons .o_gantt_buttons_container button > i.fa-caret-down"
    );
    await animationFrame();
    await click(".o_popover.dropdown-menu .o_gantt_button_auto_plan"); // click on copy button in desktop view
    await animationFrame();
    expect(".o_notification").toHaveCount(2, { message: "2 notifications should be displayed." });
    expect(".o_notification .bg-success").toHaveCount(2, {
        message: "Both notifications should be a success notification.",
    });
    expect(".o_notification button .fa-undo").toHaveCount(2, {
        message: "Both notifications should have an undo button.",
    });
    expect(getFacetTexts()).toEqual(["Shifts Planned"], {
        message: "Shifts Planned facet should be still active.",
    });
    expect(".o_gantt_pill").toHaveCount(2, { message: "2 pills should be in the gantt view." });
});

test("Verify Hours in Planning Dialog When Clicking on cell for Off Days and Working Days in Gantt View", async function () {
    mockDate("2022-10-13 00:00:00", +1);
    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);
    await mountGanttView({
        resModel: "planning.slot",
        arch: `
            <gantt
                js_class="planning_gantt"
                default_scale="month"
                date_start="start_datetime"
                date_stop="end_datetime"
                plan="0"
                display_unavailability="1"
                default_group_by="resource_id"
            />
        `,
    });
    await hoverGridCell("14 October 2022", "Open Shifts");
    await clickCell("14 October 2022", "Open Shifts");
    await waitFor(".o_dialog .o_form_view");
    expect(`.o_field_widget[name="start_datetime"] input`).toHaveValue("10/14/2022 00:00:00", {
        message: "The start date should be the minimum time for the selected date.",
    });
    expect(`.o_field_widget[name="end_datetime"] input`).toHaveValue("10/15/2022 00:00:00", {
        message: "The end date should be the maximum time for the selected date.",
    });
    await contains(`.modal-dialog .o_form_button_save`).click();
});

test("Verify Hours in Planning Dialog When Clicking 'New' Button for Off Days in Gantt View", async function () {
    mockDate("2024-10-19 00:00:00", +1);
    const unavailabilities = {
        resource_id: {
            false: [
                {
                    start: "2024-10-17 10:00:00",
                    stop: "2024-10-20 14:00:00",
                },
            ],
        },
    };
    onRpc("get_gantt_data", ({ parent }) => {
        const result = parent();
        result.unavailabilities = unavailabilities;
        return result;
    });
    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);
    await mountGanttView({
        resModel: "planning.slot",
        arch: `
            <gantt
                js_class="planning_gantt"
                default_scale="week"
                date_start="start_datetime"
                date_stop="end_datetime"
                display_unavailability="1"
                default_group_by="resource_id"
            />
        `,
    });

    click(".o_gantt_button_add.btn-primary");
    await animationFrame();
    await waitFor(".o_dialog .o_form_view");
    expect(`.o_field_widget[name="start_datetime"] input`).toHaveValue("10/19/2024 00:00:00", {
        message: "The start date should be the minimum time for the selected date",
    });
    expect(`.o_field_widget[name="end_datetime"] input`).toHaveValue("10/19/2024 23:59:59", {
        message: "The end date should be the maximum time for the selected date.",
    });
    await contains(`.modal-dialog .o_form_button_save`).click();
});

test("The date should take into the account when created through the button in Gantt View", async function () {
    mockDate("2022-12-10 07:00:00");
    PlanningSlot._records.push({
        name: "First Record",
        start_datetime: "2022-12-07 09:00:00",
        end_datetime: "2022-12-07 18:00:00",
        resource_id: 1,
    });

    PlanningSlot._views = {
        form: `
            <form>
               <field name="name"/>
                <field name="start_datetime"/>
                <field name="end_datetime"/>
                <field name="resource_id"/>
            </form>
        `,
    };

    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);

    await mountGanttView({
        resModel: "planning.slot",
        arch: `<gantt js_class="planning_gantt" date_start="start_datetime"
                date_stop="end_datetime" default_scale="week" sample="1" plan="false"/>`,
        groupBy: ["resource_id"],
    });

    await clickCell("09 W49 2022", "Resource 1");
    await contains(".modal .o_form_view .o_field_widget[name=name] input").edit("New Shift");
    await clickSave();

    expect(queryAllTexts(".o_gantt_pill_wrapper")).toEqual(["First Record", "New Shift"], {
        message: "Records should be match for Shifts",
    });

    expect(
        queryAll(".o_gantt_pill_wrapper").map((node) => node.style.gridRow.split(" / ")[0])
    ).toEqual(["r2", "r2"], { message: "The record should be added to the Resource column" });
});

test("Gantt Popover delete confirmation", async () => {
    const ganttViewProps = _getCreateViewArgsForGanttViewTotalsTests();
    ganttViewProps.groupBy = ["resource_id"];
    await mountGanttView(ganttViewProps);

    expect(".o_gantt_pill:not(.o_gantt_consolidated_pill)").toHaveCount(1);

    click(".o_gantt_pill");
    await animationFrame();

    click("button:contains('Delete')");
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    expect(".modal-title").toHaveText("Confirmation");
    click(".o_dialog button:contains('Delete')");
    await animationFrame();

    expect(".o_gantt_pill:not(.o_gantt_consolidated_pill)").toHaveCount(0);
});

test("Gantt Popover recurrence delete confirmation in mode subsequent", async () => {
    await reccureneceDeletionTemplate("subsequent");
});

test("Gantt Popover recurrence delete confirmation in mode all", async () => {
    await reccureneceDeletionTemplate("all");
});

test("date_start in url", async function () {
    PlanningSlot._records = [];
    PlanningSlot._views = {
        gantt: `
            <gantt
                js_class="planning_gantt"
                date_start="start_datetime"
                date_stop="end_datetime"
            />`,
    };

    redirect(`/web?date_start=2020-12-10#action=1&view_type=gantt`);
    await mountWithCleanup(WebClient);
    await animationFrame();

    const { groupHeaders, range } = getGridContent();
    expect(groupHeaders.map((gh) => gh.title)).toEqual(["December 2020"]);
    expect(range).toEqual("December 2020");
});

test("date_start and date_end in url (same week)", async function () {
    PlanningSlot._records = [];
    PlanningSlot._views = {
        gantt: `
            <gantt
                js_class="planning_gantt"
                date_start="start_datetime"
                date_stop="end_datetime"
            />`,
    };

    redirect(`/web?date_start=2020-12-06&date_end=2020-12-10#action=1&view_type=gantt`);
    await mountWithCleanup(WebClient);
    await animationFrame();

    const { groupHeaders, range } = getGridContent();
    expect(groupHeaders.map((gh) => gh.title)).toEqual(["W50 2020"]);
    expect(range).toEqual("W50 2020");
});

test("date_start and date_end in url (same month)", async function () {
    PlanningSlot._records = [];
    PlanningSlot._views = {
        gantt: `
            <gantt
                js_class="planning_gantt"
                date_start="start_datetime"
                date_stop="end_datetime"
            />`,
    };

    redirect(`/web?date_start=2020-12-06&date_end=2020-12-24#action=1&view_type=gantt`);
    await mountWithCleanup(WebClient);
    await animationFrame();

    const { groupHeaders, range } = getGridContent();
    expect(groupHeaders.map((gh) => gh.title)).toEqual(["December 2020"]);
    expect(range).toEqual("December 2020");
});

test("date_start and date_end in url (not in same month)", async function () {
    PlanningSlot._records = [];
    PlanningSlot._views = {
        gantt: `
            <gantt
                js_class="planning_gantt"
                date_start="start_datetime"
                date_stop="end_datetime"
            />`,
    };

    redirect(`/web?date_start=2020-12-06&date_end=2021-01-04#action=1&view_type=gantt`);
    await mountWithCleanup(WebClient);
    await animationFrame();

    const { groupHeaders, range } = getGridContent();
    expect(groupHeaders.map((gh) => gh.title)).toEqual(["December 2020", "January 2021"]);
    expect(range).toEqual("12/06/2020 -> 01/04/2021");
});

test("publish on gantt view: default end_datetime should cover full range", async function () {
    expect.assertions(10);

    mockTimeZone(0);
    mockDate("2018-11-20 18:00:00");
    // Expect env localization with {weekStart: 7}
    const ranges = [
        ["Today", "2018-11-20 23:59:59"],
        ["This week", "2018-11-24 23:59:59"],
        ["This month", "2018-11-30 23:59:59"],
        ["This quarter", "2018-12-31 23:59:59"],
        ["This year", "2018-12-31 23:59:59"],
    ];
    PlanningSlot._records.push({
        name: "First Record",
        start_datetime: "2018-11-20 07:00:00",
        end_datetime: "2018-11-20 17:00:00",
        resource_id: 1,
    });
    onRpc("gantt_resource_work_interval", ganttResourceWorkIntervalRPC);

    await mountGanttView({
        resModel: "planning.slot",
        arch: `
            <gantt
                js_class="planning_gantt"
                date_start="start_datetime"
                date_stop="end_datetime"
            />
        `,
    });

    let currentExpectedDate = null;
    patchWithCleanup(getService("action"), {
        async doAction(action, options) {
            expect(action).toBe("planning.planning_send_action", {
                message: "should open 'Send Planning By Email' form view",
            });
            expect(options.additionalContext.default_end_datetime).toBe(currentExpectedDate);
        },
    });

    for (const [label, date] of ranges) {
        currentExpectedDate = date;

        await selectRange(label);

        click(".o_gantt_button_send_all.btn-primary");
        await animationFrame();
    }
});
