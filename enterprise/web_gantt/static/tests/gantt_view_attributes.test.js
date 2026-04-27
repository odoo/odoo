import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, leave, queryAll, queryOne, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { contains, defineParams, onRpc } from "@web/../tests/web_test_helpers";
import { Tasks, defineGanttModels } from "./gantt_mock_models";
import {
    SELECTORS,
    clickCell,
    getActiveScale,
    getCell,
    getCellColorProperties,
    getGridContent,
    getPill,
    getPillWrapper,
    hoverGridCell,
    mountGanttView,
    resizePill,
} from "./web_gantt_test_helpers";

describe.current.tags("desktop");

defineGanttModels();
beforeEach(() => {
    mockDate("2018-12-20T07:00:00", +1);
    defineParams({
        lang_parameters: {
            time_format: "%I:%M:%S",
        },
    });
});

test("create attribute", async () => {
    Tasks._views.list = `<list><field name="name"/></list>`;
    Tasks._views.search = `<search><field name="name"/></search>`;
    onRpc("has_group", () => true);
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" create="0"/>`,
    });
    expect(".o_dialog").toHaveCount(0);
    await hoverGridCell("06 December 2018");
    await clickCell("06 December 2018");
    expect(".o_dialog").toHaveCount(1);
    expect(".modal-title").toHaveText("Plan");
    expect(".o_create_button").toHaveCount(0);
});

test("plan attribute", async () => {
    Tasks._views.form = `<form><field name="name"/></form>`;
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" plan="0"/>`,
    });
    expect(".o_dialog").toHaveCount(0);
    await hoverGridCell("06 December 2018");
    await clickCell("06 December 2018");
    expect(".o_dialog").toHaveCount(1);
    expect(".modal-title").toHaveText("Create");
});

test("edit attribute", async () => {
    Tasks._views.form = `<form><field name="name"/></form>`;
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" edit="0"/>`,
    });
    expect(SELECTORS.resizable).toHaveCount(0);
    expect(SELECTORS.draggable).toHaveCount(0);
    expect(getGridContent().rows).toEqual([
        {
            pills: [
                {
                    title: "Task 5",
                    level: 0,
                    colSpan: "Out of bounds (1)  -> 04 (1/2) December 2018",
                },
                { title: "Task 1", level: 1, colSpan: "Out of bounds (1)  -> 31 December 2018" },
                {
                    title: "Task 2",
                    level: 0,
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                },
                {
                    title: "Task 4",
                    level: 2,
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                },
                {
                    title: "Task 7",
                    level: 2,
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                },
                { title: "Task 3", level: 0, colSpan: "27 December 2018 -> 03 (1/2) January 2019" },
            ],
        },
    ]);

    await contains(getPill("Task 1")).click();
    expect(`.o_popover button.btn-primary`).toHaveText(/view/i);
    await contains(`.o_popover button.btn-primary`).click();
    expect(".modal .o_form_readonly").toHaveCount(1);
});

test("total_row attribute", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" total_row="1"/>`,
    });

    const { rows } = getGridContent();
    expect(rows).toEqual([
        {
            pills: [
                {
                    title: "Task 5",
                    level: 0,
                    colSpan: "Out of bounds (1)  -> 04 (1/2) December 2018",
                },
                { title: "Task 1", level: 1, colSpan: "Out of bounds (1)  -> 31 December 2018" },
                {
                    title: "Task 2",
                    level: 0,
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                },
                {
                    title: "Task 4",
                    level: 2,
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                },
                {
                    title: "Task 7",
                    level: 2,
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                },
                { title: "Task 3", level: 0, colSpan: "27 December 2018 -> 03 (1/2) January 2019" },
            ],
        },
        {
            isTotalRow: true,
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 04 (1/2) December 2018",
                    level: 0,
                    title: "2",
                },
                {
                    colSpan: "04 (1/2) December 2018 -> 17 (1/2) December 2018",
                    level: 0,
                    title: "1",
                },
                {
                    colSpan: "17 (1/2) December 2018 -> 19 December 2018",
                    level: 0,
                    title: "2",
                },
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    level: 0,
                    title: "3",
                },
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    level: 0,
                    title: "3",
                },
                {
                    colSpan: "21 December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "2",
                },
                {
                    colSpan: "22 (1/2) December 2018 -> 26 December 2018",
                    level: 0,
                    title: "1",
                },
                {
                    colSpan: "27 December 2018 -> 31 December 2018",
                    level: 0,
                    title: "2",
                },
                {
                    colSpan: "01 January 2019 -> 03 (1/2) January 2019",
                    level: 0,
                    title: "1",
                },
            ],
        },
    ]);
});

test("default_scale attribute", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day"/>`,
    });
    expect(getActiveScale()).toBe(5); // day scale
    const { columnHeaders, range } = getGridContent();
    expect(range).toBe("12/20/2018 -> 12/22/2018");
    expect(columnHeaders).toHaveLength(38);
});

test("default_scale attribute excluded from scales", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day" scales="week"/>`,
    });
    const { columnHeaders, range } = getGridContent();
    expect(range).toBe("12/20/2018 -> 12/22/2018");
    expect(columnHeaders).toHaveLength(38);
});

test("default_scale omitted, scales provided", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" scales="day,week"/>`,
    });
    const { columnHeaders, range } = getGridContent();
    expect(range).toBe("12/20/2018 -> 12/22/2018");
    expect(columnHeaders).toHaveLength(38);
});

test("scales attribute", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" scales="month,day,trololo"/>`,
    });
    expect(queryOne(".o_gantt_renderer_controls input").max).toBe("1", {
        message: "there are only 2 valid scales (starting from 0)",
    });
    expect(getActiveScale()).toBe(1);
});

test("precision attribute", async () => {
    onRpc("write", ({ args }) => expect.step(args));
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                precision="{'day': 'hour:quarter', 'week': 'day:half', 'month': 'day', 'year': 'month:quarter'}"
                default_scale="day"
            />
        `,
        domain: [["id", "=", 7]],
    });

    // resize of a quarter
    const drop = await resizePill(getPillWrapper("Task 7"), "end", 0.25, false);
    await animationFrame();
    expect(SELECTORS.resizeBadge).toHaveText("+15 minutes");

    // manually trigger the drop to trigger a write
    await drop();
    await animationFrame();
    expect(SELECTORS.resizeBadge).toHaveCount(0);
    expect.verifySteps([[[7], { stop: "2018-12-20 18:44:59" }]]);
});

test("progress attribute", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt string="Tasks" date_start="start" date_stop="stop" progress="progress"/>`,
        groupBy: ["project_id"],
    });
    expect(`${SELECTORS.pill} .o_gantt_progress`).toHaveCount(3);
    expect(
        queryAll(SELECTORS.pill).map((el) => ({
            text: el.innerText,
            progress: el.querySelector(".o_gantt_progress")?.style?.width || null,
        }))
    ).toEqual([
        { text: "Task 1", progress: null },
        { text: "Task 2", progress: "30%" },
        { text: "Task 4", progress: null },
        { text: "Task 3", progress: "60%" },
        { text: "Task 7", progress: "80%" },
    ]);
});

test("form_view_id attribute", async () => {
    Tasks._views[["form", 42]] = `<form><field name="name"/></form>`;
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt string="Tasks" date_start="start" date_stop="stop" form_view_id="42"/>`,
        groupBy: ["project_id"],
    });
    onRpc("get_views", ({ kwargs }) => expect.step(["get_views", kwargs.views]));
    await contains(queryFirst(SELECTORS.addButton + ":visible")).click();
    expect(".modal .o_form_view").toHaveCount(1);
    expect.verifySteps([
        ["get_views", [[42, "form"]]], // get_views when form view dialog opens
    ]);
});

test("decoration attribute", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" decoration-info="stage == 'todo'">
                <field name="stage"/>
            '</gantt>
        `,
    });
    expect(getPill("Task 1")).toHaveClass("decoration-info");
    expect(getPill("Task 2")).not.toHaveClass("decoration-info");
});

test("decoration attribute with date", async () => {
    mockDate("2018-12-19T12:00:00");
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" decoration-danger="start &lt; today"/>`,
    });
    expect(getPill("Task 1")).toHaveClass("decoration-danger");
    expect(getPill("Task 2")).toHaveClass("decoration-danger");
    expect(getPill("Task 5")).toHaveClass("decoration-danger");
    expect(getPill("Task 3")).not.toHaveClass("decoration-danger");
    expect(getPill("Task 4")).not.toHaveClass("decoration-danger");
    expect(getPill("Task 7")).not.toHaveClass("decoration-danger");
});

test("consolidation feature", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                consolidation="progress"
                consolidation_max="{'user_id': 100}"
                consolidation_exclude="exclude"
                progress="progress"
            />
        `,
        groupBy: ["user_id", "project_id", "stage"],
    });

    const { rows } = getGridContent();
    expect(rows).toHaveLength(18);
    expect(rows.filter((r) => r.isGroup)).toHaveLength(12);
    expect(".o_gantt_row_headers").toHaveCount(1);

    // Check grouped rows
    expect(rows[0].isGroup).toBe(true);
    expect(rows[0].title).toBe("User 1");
    expect(rows[9].isGroup).toBe(true);
    expect(rows[9].title).toBe("User 2");

    // Consolidation
    // 0 over the size of Task 5 (Task 5 is 100 but is excluded!) then 0 over the rest of Task 1, cut by Task 4 which has progress 0
    expect(rows[0].pills).toEqual([
        { colSpan: "Out of bounds (8)  -> 19 December 2018", title: "0" },
        { colSpan: "20 December 2018 -> 20 (1/2) December 2018", title: "0" },
        { colSpan: "20 (1/2) December 2018 -> 31 December 2018", title: "0" },
    ]);

    // 30 over Task 2 until Task 7 then 110 (Task 2 (30) + Task 7 (80)) then 30 again until end of task 2 then 60 over Task 3
    expect(rows[9].pills).toEqual([
        { colSpan: "17 (1/2) December 2018 -> 20 (1/2) December 2018", title: "30" },
        { colSpan: "20 (1/2) December 2018 -> 20 December 2018", title: "110" },
        { colSpan: "21 December 2018 -> 22 (1/2) December 2018", title: "30" },
        { colSpan: "27 December 2018 -> 03 (1/2) January 2019", title: "60" },
    ]);

    const withStatus = [];
    for (const el of queryAll(".o_gantt_consolidated_pill")) {
        if (el.classList.contains("bg-success") || el.classList.contains("bg-danger")) {
            withStatus.push({
                title: el.title,
                danger: el.classList.contains("border-danger"),
            });
        }
    }

    expect(withStatus).toEqual([
        { title: "0", danger: false },
        { title: "0", danger: false },
        { title: "0", danger: false },
        { title: "30", danger: false },
        { title: "110", danger: true },
        { title: "30", danger: false },
        { title: "60", danger: false },
    ]);
});

test("consolidation feature (single level)", async () => {
    Tasks._views.form = `
        <form>
            <field name="name"/>
            <field name="start"/>
            <field name="stop"/>
            <field name="project_id"/>
        </form>
    `;
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" consolidation="progress" consolidation_max="{'user_id': 100}" consolidation_exclude="exclude"/>`,
        groupBy: ["user_id"],
    });

    const { rows, range } = getGridContent();
    expect(range).toBe("12/01/2018 -> 02/28/2019");
    expect(".o_gantt_button_expand_rows").toHaveCount(1);
    expect(rows).toEqual([
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "Out of bounds (8)  -> 19 December 2018",
                    title: "0",
                },
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    title: "0",
                },
                {
                    colSpan: "20 (1/2) December 2018 -> 31 December 2018",
                    title: "0",
                },
            ],
            title: "User 1",
        },
        {
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    level: 1,
                    title: "Task 1",
                },
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    level: 0,
                    title: "Task 4",
                },
            ],
            title: "",
        },
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 20 (1/2) December 2018",
                    title: "30",
                },
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    title: "110",
                },
                {
                    colSpan: "21 December 2018 -> 22 (1/2) December 2018",
                    title: "30",
                },
                {
                    colSpan: "27 December 2018 -> 03 (1/2) January 2019",
                    title: "60",
                },
            ],
            title: "User 2",
        },
        {
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    level: 1,
                    title: "Task 7",
                },
                {
                    colSpan: "27 December 2018 -> 03 (1/2) January 2019",
                    level: 0,
                    title: "Task 3",
                },
            ],
            title: "",
        },
    ]);
});

test("color attribute", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" color="color"/>`,
    });
    expect(getPill("Task 1")).toHaveClass("o_gantt_color_0");
    expect(getPill("Task 2")).toHaveClass("o_gantt_color_2");
});

test("color attribute in multi-level grouped", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" color="color"/>`,
        groupBy: ["user_id", "project_id"],
        domain: [["id", "=", 1]],
    });
    expect(`${SELECTORS.pill}.o_gantt_consolidated_pill`).not.toHaveClass("o_gantt_color_0");
    expect(`${SELECTORS.pill}:not(.o_gantt_consolidated_pill)`).toHaveClass("o_gantt_color_0");
});

test("color attribute on a many2one", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" color="project_id"/>`,
    });
    expect(getPill("Task 1")).toHaveClass("o_gantt_color_1");
    expect(`${SELECTORS.pill}.o_gantt_color_1`).toHaveCount(4);
    expect(`${SELECTORS.pill}.o_gantt_color_2`).toHaveCount(2);
});

test(`Today style with unavailabilities ("week": "day:half")`, async () => {
    const unavailabilities = [
        {
            start: "2018-12-18 10:00:00",
            stop: "2018-12-20 14:00:00",
        },
    ];

    onRpc("get_gantt_data", ({ parent }) => {
        const result = parent();
        result.unavailabilities.__default = { false: unavailabilities };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" display_unavailability="1" default_scale="week" scales="week" precision="{'week': 'day:half'}"/>`,
    });

    // Normal day / unavailability
    expect(getCellColorProperties("18 W51 2018")).toEqual([
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
    ]);

    // Full unavailability
    expect(getCellColorProperties("19 W51 2018")).toEqual(["--Gantt__DayOff-background-color"]);

    // Unavailability / today
    expect(getCell("20 W51 2018")).toHaveClass("o_gantt_today");
    expect(getCellColorProperties("20 W51 2018")).toEqual([
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOffToday-background-color",
    ]);
});

test("Today style of group rows", async () => {
    const unavailabilities = [
        {
            start: "2018-12-18 10:00:00",
            stop: "2018-12-20 14:00:00",
        },
    ];
    Tasks._records = [Tasks._records[3]]; // id: 4

    onRpc("get_gantt_data", ({ parent }) => {
        expect.step("get_gantt_data");
        const result = parent();
        result.unavailabilities.project_id = { 1: unavailabilities };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" display_unavailability="1" default_scale="week" scales="week" precision="{'week': 'day:half'}"/>`,
        groupBy: ["user_id", "project_id"],
    });
    expect.verifySteps(["get_gantt_data"]);

    // Normal group cell: open
    let cell4 = getCell("19 W51 2018");
    expect(cell4).not.toHaveClass("o_gantt_today");
    expect(cell4).toHaveClass("o_group_open");
    expect(cell4).toHaveStyle({
        backgroundImage: "linear-gradient(rgb(249, 250, 251), rgb(234, 237, 241))",
    });

    // Today group cell: open
    let cell5 = getCell("20 W51 2018");
    expect(cell5).toHaveClass("o_gantt_today");
    expect(cell5).toHaveClass("o_group_open");
    expect(cell5).toHaveStyle({
        backgroundImage: "linear-gradient(rgb(249, 250, 251), rgb(234, 237, 241))",
    });
    await contains(SELECTORS.group).click(); // fold group
    await leave();
    // Normal group cell: closed
    cell4 = getCell("19 W51 2018");
    expect(cell4).not.toHaveClass("o_gantt_today");
    expect(cell4).not.toHaveClass("o_group_open");
    expect(cell4).toHaveStyle({
        backgroundImage: "linear-gradient(rgb(234, 237, 241), rgb(249, 250, 251))",
    });

    // Today group cell: closed
    cell5 = getCell("20 W51 2018");
    expect(cell5).toHaveClass("o_gantt_today");
    expect(cell5).not.toHaveClass("o_group_open");
    expect(cell5).toHaveStyle({ backgroundImage: "none" });
    expect(cell5).toHaveStyle({ backgroundColor: "rgb(252, 250, 243)" });
});

test("style without unavailabilities", async () => {
    mockDate("2018-12-05T02:00:00");

    onRpc("get_gantt_data", ({ kwargs }) => {
        expect.step("get_gantt_data");
        expect(kwargs.unavailability_fields).toEqual([]);
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" display_unavailability="1"/>`,
    });
    expect.verifySteps(["get_gantt_data"]);
    const cell5 = getCell("05 December 2018");
    expect(cell5).toHaveClass("o_gantt_today");
    expect(cell5).toHaveAttribute("style", "grid-column:c9/c11;grid-row:r1/r5;");
    const cell6 = getCell("06 December 2018");
    expect(cell6).toHaveAttribute("style", "grid-column:c11/c13;grid-row:r1/r5;");
});

test(`Unavailabilities ("month": "day:half")`, async () => {
    mockDate("2018-12-05T02:00:00");

    const unavailabilities = [
        {
            start: "2018-12-05 09:30:00",
            stop: "2018-12-07 08:00:00",
        },
        {
            start: "2018-12-16 09:00:00",
            stop: "2018-12-18 13:00:00",
        },
    ];
    onRpc("get_gantt_data", ({ model, kwargs, parent }) => {
        expect.step("get_gantt_data");
        expect(model).toBe("tasks");
        expect(kwargs.unavailability_fields).toEqual([]);
        expect(kwargs.start_date).toBe("2018-11-30 23:00:00");
        expect(kwargs.stop_date).toBe("2019-02-28 23:00:00");
        const result = parent();
        result.unavailabilities = { __default: { false: unavailabilities } };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" display_unavailability="1"/>`,
    });
    expect.verifySteps(["get_gantt_data"]);
    expect(getCell("05 December 2018")).toHaveClass("o_gantt_today");
    expect(getCellColorProperties("05 December 2018")).toEqual([
        "--Gantt__DayOffToday-background-color",
        "--Gantt__DayOff-background-color",
    ]);
    expect(getCellColorProperties("06 December 2018")).toEqual([
        "--Gantt__DayOff-background-color",
    ]);
    expect(getCellColorProperties("07 December 2018")).toEqual([]);
    expect(getCellColorProperties("16 December 2018")).toEqual([
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
    ]);
    expect(getCellColorProperties("17 December 2018")).toEqual([
        "--Gantt__DayOff-background-color",
    ]);
    expect(getCellColorProperties("18 December 2018")).toEqual([
        "--Gantt__DayOff-background-color",
        "--Gantt__Day-background-color",
    ]);
});

test(`Unavailabilities ("day": "hours:quarter")`, async () => {
    Tasks._records = [];
    const unavailabilities = [
        // in utc
        {
            start: "2018-12-20 08:15:00",
            stop: "2018-12-20 08:30:00",
        },
        {
            start: "2018-12-20 10:35:00",
            stop: "2018-12-20 12:29:00",
        },
        {
            start: "2018-12-20 20:15:00",
            stop: "2018-12-20 20:50:00",
        },
    ];
    onRpc("get_gantt_data", ({ kwargs, parent }) => {
        expect(kwargs.unavailability_fields).toEqual([]);
        const result = parent();
        result.unavailabilities = { __default: { false: unavailabilities } };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" display_unavailability="1" default_scale="day" scales="day" precision="{'day': 'hours:quarter'}"/>`,
    });
    expect(getCellColorProperties("9am 20 December 2018")).toEqual([
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
    ]);
    expect(getCellColorProperties("11am 20 December 2018")).toEqual([
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
    ]);
    expect(getCellColorProperties("12pm 20 December 2018")).toEqual([
        "--Gantt__DayOff-background-color",
    ]);
    expect(getCellColorProperties("1pm 20 December 2018")).toEqual([
        "--Gantt__DayOff-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
    ]);
    expect(getCellColorProperties("9pm 20 December 2018")).toEqual([
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__Day-background-color",
    ]);
});

test("offset attribute", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" offset="-4" default_scale="day"/>`,
    });

    const { range } = getGridContent();
    expect(range).toBe("12/16/2018 -> 12/18/2018", {
        message: "gantt view should be set to 4 days before initial date",
    });
});

test("default_group_by attribute", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_group_by="user_id"/>`,
    });

    const { rows } = getGridContent();
    expect(rows).toEqual([
        {
            title: "User 1",
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    level: 1,
                    title: "Task 1",
                },
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    level: 0,
                    title: "Task 4",
                },
            ],
        },
        {
            title: "User 2",
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    level: 1,
                    title: "Task 7",
                },
                {
                    colSpan: "27 December 2018 -> 03 (1/2) January 2019",
                    level: 0,
                    title: "Task 3",
                },
            ],
        },
    ]);
});

test("default_group_by attribute with groupBy", async () => {
    // The default_group_by attribute should be ignored if a groupBy is given.
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_group_by="user_id"/>`,
        groupBy: ["project_id"],
    });

    const { rows } = getGridContent();
    expect(rows).toEqual([
        {
            title: "Project 1",
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    level: 0,
                    title: "Task 1",
                },
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 1,
                    title: "Task 2",
                },
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    level: 2,
                    title: "Task 4",
                },
                {
                    colSpan: "27 December 2018 -> 03 (1/2) January 2019",
                    level: 1,
                    title: "Task 3",
                },
            ],
        },
        {
            title: "Project 2",
            pills: [
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    level: 0,
                    title: "Task 7",
                },
            ],
        },
    ]);
});

test("default_group_by attribute with 2 fields", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_group_by="user_id,project_id"/>`,
    });

    const { rows } = getGridContent();
    expect(rows).toEqual([
        {
            title: "User 1",
            isGroup: true,
            pills: [
                {
                    colSpan: "Out of bounds (8)  -> 19 December 2018",
                    title: "1",
                },
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    title: "2",
                },
                {
                    colSpan: "20 (1/2) December 2018 -> 31 December 2018",
                    title: "1",
                },
            ],
        },
        {
            title: "Project 1",
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    level: 0,
                    title: "Task 1",
                },
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    level: 1,
                    title: "Task 4",
                },
            ],
        },
        {
            title: "Project 2",
        },
        {
            title: "User 2",
            isGroup: true,
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 20 (1/2) December 2018",
                    title: "1",
                },
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    title: "2",
                },
                {
                    colSpan: "21 December 2018 -> 22 (1/2) December 2018",
                    title: "1",
                },
                {
                    colSpan: "27 December 2018 -> 03 (1/2) January 2019",
                    title: "1",
                },
            ],
        },
        {
            title: "Project 1",
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
                {
                    colSpan: "27 December 2018 -> 03 (1/2) January 2019",
                    level: 0,
                    title: "Task 3",
                },
            ],
        },
        {
            title: "Project 2",
            pills: [
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    level: 0,
                    title: "Task 7",
                },
            ],
        },
    ]);
});

test("default_range attribute", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_range="day"/>`,
    });
    expect(getActiveScale()).toBe(2); // month scale
    const { columnHeaders, range } = getGridContent();
    expect(range).toBe("12/20/2018");
    expect(columnHeaders).toHaveLength(1);
    await click(SELECTORS.rangeMenuToggler);
    await animationFrame();
    const firstRangeMenuItem = queryFirst(`${SELECTORS.rangeMenu} .dropdown-item`);
    expect(firstRangeMenuItem).toHaveClass("selected");
    expect(firstRangeMenuItem).toHaveText("Today");
});

test("consolidation and unavailabilities", async () => {
    const unavailabilities = [
        {
            start: "2018-12-18 10:00:00",
            stop: "2018-12-20 14:00:00",
        },
    ];
    onRpc("get_gantt_data", ({ parent, kwargs }) => {
        expect.step("get_gantt_data");
        const result = parent();
        expect(kwargs.unavailability_fields).toEqual(["user_id"]);
        result.unavailabilities.user_id = { 1: unavailabilities };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                consolidation="progress"
                consolidation_max="{'user_id': 100}"
                consolidation_exclude="exclude"
                display_unavailability="1"
            />
        `,
        groupBy: ["user_id"],
    });
    expect.verifySteps(["get_gantt_data"]);
    // Normal day / unavailability
    expect(getCellColorProperties("18 December 2018", "", { num: 2 })).toEqual([
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
    ]);

    // Full unavailability
    expect(getCellColorProperties("19 December 2018", "", { num: 2 })).toEqual([
        "--Gantt__DayOff-background-color",
    ]);

    // Unavailability / today
    expect(getCell("20 December 2018")).toHaveClass("o_gantt_today");
    expect(getCellColorProperties("20 December 2018", "", { num: 2 })).toEqual([
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOffToday-background-color",
    ]);
});

test("default_range not in scales", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" scales="month" default_range="year"/>`,
    });
    const { range } = getGridContent();
    expect(range).toBe("2018");
});
