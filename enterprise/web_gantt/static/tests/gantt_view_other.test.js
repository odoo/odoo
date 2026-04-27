import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { onRendered, useEffect, useRef } from "@odoo/owl";
import {
    contains,
    defineParams,
    fields,
    getService,
    mountWithCleanup,
    onRpc,
    pagerNext,
    patchWithCleanup,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { Tasks, defineGanttModels } from "./gantt_mock_models";
import {
    CLASSES,
    SELECTORS,
    clickCell,
    dragPill,
    editPill,
    ganttControlsChanges,
    getGridContent,
    hoverGridCell,
    mountGanttView,
    selectGanttRange,
    setScale,
} from "./web_gantt_test_helpers";

import { Domain } from "@web/core/domain";
import { WebClient } from "@web/webclient/webclient";
import { GanttController } from "@web_gantt/gantt_controller";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { GanttRowProgressBar } from "@web_gantt/gantt_row_progress_bar";

// Hard-coded daylight saving dates from 2019
const DST_DATES = {
    winterToSummer: {
        before: "2019-03-30",
        after: "2019-03-31",
    },
    summerToWinter: {
        before: "2019-10-26",
        after: "2019-10-27",
    },
};

describe.current.tags("desktop");

defineGanttModels();
beforeEach(() => {
    mockDate("2018-12-20T08:00:00", +1);
    defineParams({
        lang_parameters: {
            time_format: "%I:%M:%S",
        },
    });
});

test("DST spring forward", async () => {
    mockTimeZone("Europe/Brussels");
    Tasks._records = [
        {
            id: 1,
            name: "DST Task 1",
            start: `${DST_DATES.winterToSummer.before} 03:00:00`,
            stop: `${DST_DATES.winterToSummer.before} 03:30:00`,
        },
        {
            id: 2,
            name: "DST Task 2",
            start: `${DST_DATES.winterToSummer.after} 03:00:00`,
            stop: `${DST_DATES.winterToSummer.after} 03:30:00`,
        },
    ];
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day"/>`,
        context: {
            initialDate: `${DST_DATES.winterToSummer.before} 08:00:00`,
        },
    });

    const { columnHeaders, rows } = getGridContent();
    expect(columnHeaders.slice(0, 4).map((h) => h.title)).toEqual(["12am", "1am", "2am", "3am"]);
    expect(columnHeaders.slice(24, 28).map((h) => h.title)).toEqual(["12am", "1am", "3am", "4am"]);
    expect(rows[0].pills).toEqual([
        {
            colSpan: "4am 30 March 2019 -> 4am 30 March 2019",
            level: 0,
            title: "DST Task 1",
        },
        {
            colSpan: "5am 31 March 2019 -> 5am 31 March 2019",
            level: 0,
            title: "DST Task 2",
        },
    ]);
});

test("DST fall back", async () => {
    mockTimeZone("Europe/Brussels");
    Tasks._records = [
        {
            id: 1,
            name: "DST Task 1",
            start: `${DST_DATES.summerToWinter.before} 03:00:00`,
            stop: `${DST_DATES.summerToWinter.before} 03:30:00`,
        },
        {
            id: 2,
            name: "DST Task 2",
            start: `${DST_DATES.summerToWinter.after} 03:00:00`,
            stop: `${DST_DATES.summerToWinter.after} 03:30:00`,
        },
    ];
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day"/>`,
        context: {
            initialDate: `${DST_DATES.summerToWinter.before} 08:00:00`,
        },
    });

    const { columnHeaders, rows } = getGridContent();
    expect(columnHeaders.slice(0, 4).map((h) => h.title)).toEqual(["12am", "1am", "2am", "3am"]);
    expect(columnHeaders.slice(24, 28).map((h) => h.title)).toEqual(["12am", "1am", "2am", "2am"]);
    expect(rows[0].pills).toEqual([
        {
            colSpan: "5am 26 October 2019 -> 5am 26 October 2019",
            level: 0,
            title: "DST Task 1",
        },
        {
            colSpan: "4am 27 October 2019 -> 4am 27 October 2019",
            level: 0,
            title: "DST Task 2",
        },
    ]);
});

test("Records spanning across DST should be displayed normally", async () => {
    mockTimeZone("Europe/Brussels");

    Tasks._records = [
        {
            id: 1,
            name: "DST Task 1",
            start: `${DST_DATES.winterToSummer.before} 03:00:00`,
            stop: `${DST_DATES.winterToSummer.after} 03:30:00`,
        },
        {
            id: 2,
            name: "DST Task 2",
            start: `${DST_DATES.summerToWinter.before} 03:00:00`,
            stop: `${DST_DATES.summerToWinter.after} 03:30:00`,
        },
    ];
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="year"/>`,
        context: {
            initialDate: `${DST_DATES.summerToWinter.before} 08:00:00`,
        },
    });
    expect(getGridContent().rows).toEqual([
        {
            pills: [
                { title: "DST Task 1", colSpan: "March 2019 -> March 2019", level: 0 },
                { title: "DST Task 2", colSpan: "October 2019 -> October 2019", level: 0 },
            ],
        },
    ]);
});

test("delete attribute on dialog", async () => {
    Tasks._views.form = `
        <form>
            <field name="name"/>
            <field name="start"/>
            <field name="stop"/>
            <field name="stage"/>
            <field name="project_id"/>
            <field name="user_id"/>
        </form>
    `;
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" delete="0"/>`,
    });
    await editPill("Task 1");
    expect(".modal").toHaveCount(1);
    expect(".o_form_button_remove").toHaveCount(0);
});

test("move a pill in multi-level group row after collapse and expand grouped row", async () => {
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args).toEqual([
            [7],
            {
                project_id: 1,
                start: "2018-12-11 12:30:12",
                stop: "2018-12-11 18:29:59",
            },
        ]);
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" />`,
        groupBy: ["project_id", "stage"],
        domain: [["id", "in", [1, 7]]],
    });
    expect(getGridContent().rows).toHaveLength(4);

    // collapse the first group
    await contains(`${SELECTORS.rowHeader}${SELECTORS.group}:nth-child(1)`).click();
    expect(`${SELECTORS.rowHeader}:nth-child(1)`).not.toHaveClass("o_group_open");
    // expand the first group
    await contains(`${SELECTORS.rowHeader}${SELECTORS.group}:nth-child(1)`).click();
    expect(`${SELECTORS.rowHeader}:nth-child(1)`).toHaveClass("o_group_open");

    // move a pill (task 7) in the other row and in the day 2
    const { drop } = await dragPill("Task 7");
    await drop({ column: "11 December 2018", part: 2 });
    expect.verifySteps(["write"]);
    expect(getGridContent().rows.filter((x) => x.isGroup)).toHaveLength(1);
});

test("plan dialog initial domain has the action domain as its only base", async () => {
    Tasks._views = {
        gantt: `<gantt date_start="start" date_stop="stop"/>`,
        list: `<list><field name="name"/></list>`,
        search: `
            <search>
                <filter name="project_one" string="Project 1" domain="[('project_id', '=', 1)]"/>
            </search>
        `,
    };
    onRpc("get_gantt_data", ({ kwargs }) => expect.step(kwargs.domain.toString()));
    onRpc("web_search_read", ({ kwargs }) => expect.step(kwargs.domain.toString()));
    await mountWithCleanup(WebClient);
    const ganttAction = {
        name: "Tasks Gantt",
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [[false, "gantt"]],
    };

    // Load action without domain and open plan dialog
    await getService("action").doAction(ganttAction);
    await animationFrame();

    expect.verifySteps(["&,start,<,2019-02-28 23:00:00,stop,>,2018-11-30 23:00:00"]);
    await hoverGridCell("10 December 2018");
    await clickCell("10 December 2018");
    expect.verifySteps(["|,start,=,false,stop,=,false"]);

    // Load action WITH domain and open plan dialog
    await getService("action").doAction({
        ...ganttAction,
        domain: [["project_id", "=", 1]],
    });
    expect.verifySteps([
        "&,project_id,=,1,&,start,<,2019-02-28 23:00:00,stop,>,2018-11-30 23:00:00",
    ]);

    await hoverGridCell("10 December 2018");
    await clickCell("10 December 2018");
    expect.verifySteps(["&,project_id,=,1,|,start,=,false,stop,=,false"]);

    // Load action without domain, activate a filter and then open plan dialog
    await getService("action").doAction(ganttAction);
    expect.verifySteps(["&,start,<,2019-02-28 23:00:00,stop,>,2018-11-30 23:00:00"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Project 1");
    expect.verifySteps([
        "&,project_id,=,1,&,start,<,2019-02-28 23:00:00,stop,>,2018-11-30 23:00:00",
    ]);

    await hoverGridCell("10 December 2018");
    await clickCell("10 December 2018");
    expect.verifySteps(["|,start,=,false,stop,=,false"]);
});

test("No progress bar when no option set.", async () => {
    onRpc("gantt_progress_bar", () => {
        throw new Error("Method should not be called");
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="week" scales="week"/>`,
    });
    expect(SELECTORS.progressBar).toHaveCount(0);
});

test("Progress bar rpc is triggered when option set.", async () => {
    onRpc("get_gantt_data", ({ kwargs, method, parent }) => {
        const result = parent();
        expect.step(method);
        expect(kwargs.progress_bar_fields).toEqual(["user_id"]);
        result.progress_bars.user_id = {
            1: { value: 50, max_value: 100 },
            2: { value: 25, max_value: 200 },
        };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" default_group_by="user_id" progress_bar="user_id">
                <field name="user_id"/>
            </gantt>
        `,
    });
    expect.verifySteps(["get_gantt_data"]);
    expect(SELECTORS.progressBar).toHaveCount(2);
    const [progressBar1, progressBar2] = queryAll(SELECTORS.progressBar);
    expect(progressBar1).toHaveClass("o_gantt_group_success");
    expect(progressBar2).toHaveClass("o_gantt_group_success");
    const [rowHeader1, rowHeader2] = [progressBar1.parentElement, progressBar2.parentElement];
    expect(rowHeader1.matches(SELECTORS.rowHeader)).toBe(true);
    expect(rowHeader2.matches(SELECTORS.rowHeader)).toBe(true);
    expect(rowHeader1).not.toHaveClass(CLASSES.group);
    expect(rowHeader2).not.toHaveClass(CLASSES.group);
    expect(queryAll(SELECTORS.progressBarBackground).map((el) => el.style.width)).toEqual([
        "50%",
        "12.5%",
    ]);
    await hoverGridCell("16 W51 2018");
    expect(SELECTORS.progressBarForeground).toHaveText("50h / 100h");
    await hoverGridCell("16 W51 2018", "User 2");
    expect(SELECTORS.progressBarForeground).toHaveText("25h / 200h");
});

test("Progress bar component will not render when hovering cells of the same row", async () => {
    patchWithCleanup(GanttRowProgressBar.prototype, {
        setup() {
            onRendered(() => expect.step("rendering progress bar"));
        },
    });
    onRpc("get_gantt_data", ({ parent }) => {
        const result = parent();
        result.progress_bars.user_id = {
            1: { value: 50, max_value: 100 },
            2: { value: 25, max_value: 200 },
        };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `
                <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" default_group_by="user_id" progress_bar="user_id">
                    <field name="user_id"/>
                </gantt>
            `,
    });
    expect.verifySteps(["rendering progress bar", "rendering progress bar"]);
    await hoverGridCell("19 W51 2018");
    expect.verifySteps(["rendering progress bar", "rendering progress bar"]);
    await hoverGridCell("18 W51 2018");
    await hoverGridCell("18 W51 2018", "User 2");
    expect.verifySteps(["rendering progress bar", "rendering progress bar"]);
});

test("Progress bar when multilevel grouped.", async () => {
    onRpc("get_gantt_data", ({ kwargs, method, parent }) => {
        const result = parent();
        expect.step(method);
        expect(kwargs.progress_bar_fields).toEqual(["user_id"]);
        result.progress_bars.user_id = {
            1: { value: 50, max_value: 100 },
            2: { value: 25, max_value: 200 },
        };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" default_group_by="user_id,user_id" progress_bar="user_id">
                <field name="user_id"/>
            </gantt>
        `,
    });
    expect.verifySteps(["get_gantt_data"]);
    expect(SELECTORS.progressBar).toHaveCount(4);
    const [progressBar1, progressBar2] = queryAll(SELECTORS.progressBar);
    expect(progressBar1).toHaveClass("o_gantt_group_success");
    expect(progressBar2).toHaveClass("o_gantt_group_success");
    const [rowHeader1, rowHeader2] = [progressBar1.parentElement, progressBar2.parentElement];
    expect(rowHeader1.matches(SELECTORS.rowHeader)).toBe(true);
    expect(rowHeader2.matches(SELECTORS.rowHeader)).toBe(true);
    expect(rowHeader1).toHaveClass(CLASSES.group);
    expect(rowHeader2).not.toHaveClass(CLASSES.group);
    expect(queryAll(SELECTORS.progressBarBackground).map((el) => el.style.width)).toEqual([
        "50%",
        "50%",
        "12.5%",
        "12.5%",
    ]);
    await hoverGridCell("16 W51 2018");
    expect(SELECTORS.progressBarForeground).toHaveText("50h / 100h");
    await hoverGridCell("16 W51 2018", "User 2");
    expect(SELECTORS.progressBarForeground).toHaveText("25h / 200h");
});

test("Progress bar warning when max_value is zero", async () => {
    onRpc("get_gantt_data", ({ kwargs, method, parent }) => {
        const result = parent();
        expect.step(method);
        expect(kwargs.progress_bar_fields).toEqual(["user_id"]);
        result.progress_bars.user_id = {
            1: { value: 50, max_value: 0 },
            warning: "plop",
        };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" default_group_by="user_id" progress_bar="user_id">
                <field name="user_id"/>
            </gantt>
        `,
    });
    expect.verifySteps(["get_gantt_data"]);
    expect(SELECTORS.progressBarWarning).toHaveCount(0);
    await hoverGridCell("16 W51 2018");
    expect(SELECTORS.progressBarWarning).toHaveCount(1);
    expect(queryFirst(SELECTORS.progressBarWarning).parentElement).toHaveText("50h");
    expect(queryFirst(SELECTORS.progressBarWarning).parentElement).toHaveProperty("title", "plop");
});

test("Progress bar when value less than hour", async () => {
    onRpc("get_gantt_data", ({ kwargs, method, parent }) => {
        const result = parent();
        expect.step(method);
        expect(kwargs.progress_bar_fields).toEqual(["user_id"]);
        result.progress_bars.user_id = {
            1: { value: 0.5, max_value: 100 },
        };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" default_group_by="user_id" progress_bar="user_id">
                <field name="user_id"/>
            </gantt>
        `,
    });
    expect.verifySteps(["get_gantt_data"]);
    expect(SELECTORS.progressBar).toHaveCount(1);
    await hoverGridCell("16 W51 2018");
    expect(SELECTORS.progressBarForeground).toHaveText("0h30 / 100h");
});

test("Progress bar danger when ratio > 100", async () => {
    onRpc("get_gantt_data", ({ kwargs, method, parent }) => {
        const result = parent();
        expect.step(method);
        expect(kwargs.progress_bar_fields).toEqual(["user_id"]);
        result.progress_bars.user_id = {
            1: { value: 150, max_value: 100 },
        };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" default_group_by="user_id" progress_bar="user_id">
                <field name="user_id"/>
            </gantt>
        `,
    });
    expect.verifySteps(["get_gantt_data"]);
    expect(SELECTORS.progressBar).toHaveCount(1);
    expect(SELECTORS.progressBarBackground).toHaveStyle("width: 100%", { inline: true });
    expect(SELECTORS.progressBar).toHaveClass("o_gantt_group_danger");
    await hoverGridCell("16 W51 2018");
    expect(queryFirst(SELECTORS.progressBarForeground).parentElement).toHaveClass("text-bg-danger");
    expect(SELECTORS.progressBarForeground).toHaveText("150h / 100h");
});

test("Falsy search field will return an empty rows", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" progress_bar="user_id">
                <field name="user_id"/>
            </gantt>
        `,
        groupBy: ["project_id", "user_id"],
        domain: [["id", "=", 5]],
    });
    expect(".o_gantt_row_sidebar_empty").toHaveCount(1);
    expect(SELECTORS.progressBar).toHaveCount(0);
});

test("Search field return rows with progressbar", async () => {
    onRpc("get_gantt_data", ({ kwargs, method, parent }) => {
        const result = parent();
        expect.step(method);
        expect(kwargs.progress_bar_fields).toEqual(["user_id"]);
        result.progress_bars.user_id = {
            2: { value: 25, max_value: 200 },
        };
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" progress_bar="user_id">
                <field name="user_id"/>
            </gantt>
        `,
        groupBy: ["project_id", "user_id"],
        domain: [["id", "=", 2]],
    });
    expect.verifySteps(["get_gantt_data"]);
    const { rows } = getGridContent();
    expect(rows.map((r) => r.title)).toEqual(["Project 1", "User 2"]);
    expect(SELECTORS.progressBar).toHaveCount(1);
    expect(SELECTORS.progressBarBackground).toHaveStyle("width: 12.5%", { inline: true });
});

test("add record in empty gantt", async () => {
    Tasks._records = [];
    Tasks._fields.stage_id.domain = "[('id', '!=', False)]";
    Tasks._views.form = `
        <form>
            <field name="stage_id" widget="statusbar"/>
            <field name="project_id"/>
            <field name="start"/>
            <field name="stop"/>
        </form>
    `;
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" plan="false"/>`,
        groupBy: ["project_id"],
    });
    await hoverGridCell("10 December 2018");
    await clickCell("10 December 2018");
    expect(".modal").toHaveCount(1);
});

test("Only the task name appears in the pill title when the pill_label option is not set", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="week" scales="week"/>`,
    });
    expect(queryAllTexts(SELECTORS.pill)).toEqual([
        "Task 1", // the pill should not include DateTime in the title
        "Task 2",
        "Task 4",
        "Task 7",
    ]);
});

test("The date and task name appears in the pill title when the pill_label option is set", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="week" scales="week" pill_label="True"/>`,
    });
    expect(queryAllTexts(SELECTORS.pill)).toEqual([
        "11/30 - 12/31 - Task 1", // the task span across in week then DateTime should be displayed on the pill label
        "Task 2", // the task does not span across in week scale then DateTime shouldn't be displayed on the pill label
        "Task 4",
        "Task 7",
    ]);
});

test("A task should always have a title (pill_label='1', scale 'week')", async () => {
    Tasks._fields.allocated_hours = fields.Float({ string: "Allocated Hours" });
    Tasks._records = [
        {
            id: 1,
            name: "Task 1",
            start: "2018-12-17 08:30:00",
            stop: "2018-12-17 19:30:00", // span only one day
            allocated_hours: 0,
        },
        {
            id: 2,
            name: "Task 2",
            start: "2018-12-18 08:30:00",
            stop: "2018-12-18 19:30:00", // span only one day
            allocated_hours: 6,
        },
        {
            id: 3,
            name: "Task 3",
            start: "2018-12-18 08:30:00",
            stop: "2018-12-19 19:30:00", // span two days
            allocated_hours: 6,
        },
        {
            id: 4,
            name: "Task 4",
            start: "2018-12-08 08:30:00",
            stop: "2019-02-18 19:30:00", // span two weeks
            allocated_hours: 6,
        },
        {
            id: 5,
            name: "Task 5",
            start: "2018-12-18 08:30:00",
            stop: "2019-02-18 19:30:00", // span two months
            allocated_hours: 6,
        },
    ];
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" pill_label="True" default_scale="week">
                <field name="allocated_hours"/>
            </gantt>
        `,
    });
    const titleMapping = [
        { name: "Task 4", title: "12/8 - 2/18 - Task 4" },
        { name: "Task 1", title: "Task 1" },
        { name: "Task 2", title: "9:30 AM - 8:30 PM (6h) - Task 2" },
        { name: "Task 3", title: "Task 3" },
        { name: "Task 5", title: "12/18 - 2/18 - Task 5" },
    ];
    expect(queryAllTexts(".o_gantt_pill")).toEqual(titleMapping.map((e) => e.title));
    const pills = queryAll(".o_gantt_pill");
    for (let i = 0; i < pills.length; i++) {
        await contains(pills[i]).click();
        expect(".o_popover .popover-header").toHaveText(titleMapping[i].name);
    }
});

test("A task should always have a title (pill_label='1', scale 'month')", async () => {
    Tasks._fields.allocated_hours = fields.Float({ string: "Allocated Hours" });
    Tasks._records = [
        {
            id: 1,
            name: "Task 1",
            start: "2018-12-15 08:30:00",
            stop: "2018-12-15 19:30:00", // span only one day
            allocated_hours: 0,
        },
        {
            id: 2,
            name: "Task 2",
            start: "2018-12-16 08:30:00",
            stop: "2018-12-16 19:30:00", // span only one day
            allocated_hours: 6,
        },
        {
            id: 3,
            name: "Task 3",
            start: "2018-12-16 08:30:00",
            stop: "2018-12-17 18:30:00", // span two days
            allocated_hours: 6,
        },
        {
            id: 4,
            name: "Task 4",
            start: "2018-12-16 08:30:00",
            stop: "2019-02-18 19:30:00", // span two months
            allocated_hours: 6,
        },
    ];
    await mountGanttView({
        resModel: "tasks",
        arch: `
            <gantt date_start="start" date_stop="stop" pill_label="True">
                <field name="allocated_hours"/>
            </gantt>
        `,
    });
    const titleMapping = [
        { name: "Task 1", title: "Task 1" },
        { name: "Task 2", title: "9:30 AM - 8:30 PM (6h)" },
        { name: "Task 3", title: "Task 3" },
        { name: "Task 4", title: "12/16 - 2/18 - Task 4" },
    ];
    expect(queryAllTexts(".o_gantt_pill")).toEqual(titleMapping.map((e) => e.title));
    const pills = queryAll(".o_gantt_pill");
    for (let i = 0; i < pills.length; i++) {
        await contains(pills[i]).click();
        expect(".o_popover .popover-header").toHaveText(titleMapping[i].name);
    }
});

test("position of no content help in sample mode", async () => {
    patchWithCleanup(GanttController.prototype, {
        setup() {
            super.setup(...arguments);
            const rootRef = useRef("root");
            useEffect(() => {
                rootRef.el.querySelector(".o_content.o_view_sample_data").style.position =
                    "relative";
            });
        },
    });
    patchWithCleanup(GanttRenderer.prototype, {
        isDisabled(row) {
            return this.rows.indexOf(row) !== 0;
        },
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" sample="1"/>`,
        groupBy: ["user_id"],
        domain: Domain.FALSE.toList(),
    });
    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_gantt_row_header:first").not.toHaveClass("o_sample_data_disabled");
    const noContentHelp = queryFirst(".o_view_nocontent");
    const noContentHelpTop = noContentHelp.getBoundingClientRect().top;
    const firstRowHeader = queryFirst(".o_gantt_row_header");
    const firstRowHeaderBottom = firstRowHeader.getBoundingClientRect().bottom;
    expect(noContentHelpTop - firstRowHeaderBottom).toBeLessThan(3);
});

test("gantt view grouped by a boolean field: row titles should be 'True' or 'False'", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
        groupBy: ["exclude"],
    });
    expect(getGridContent().rows.map((r) => r.title)).toEqual(["False", "True"]);
});

test("date grid and dst winterToSummer (1 cell part)", async () => {
    let renderer;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        },
    });

    mockTimeZone("Europe/Brussels");
    Tasks._records = [];

    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day" precision="{'day':'hour:full', 'week':'day:full', 'month':'day:full', 'year':'month:full' }"/>`,
        domain: [["id", "=", 8]],
        context: {
            initialDate: `${DST_DATES.winterToSummer.before} 08:00:00`,
        },
    });

    function getGridInfo() {
        return renderer.subColumns.map(({ start }) => start.toString());
    }
    expect(getGridInfo()).toEqual([
        "2019-03-30T00:00:00.000+01:00",
        "2019-03-30T01:00:00.000+01:00",
        "2019-03-30T02:00:00.000+01:00",
        "2019-03-30T03:00:00.000+01:00",
        "2019-03-30T04:00:00.000+01:00",
        "2019-03-30T05:00:00.000+01:00",
        "2019-03-30T06:00:00.000+01:00",
        "2019-03-30T07:00:00.000+01:00",
        "2019-03-30T08:00:00.000+01:00",
        "2019-03-30T09:00:00.000+01:00",
        "2019-03-30T10:00:00.000+01:00",
        "2019-03-30T11:00:00.000+01:00",
        "2019-03-30T12:00:00.000+01:00",
        "2019-03-30T13:00:00.000+01:00",
        "2019-03-30T14:00:00.000+01:00",
        "2019-03-30T15:00:00.000+01:00",
        "2019-03-30T16:00:00.000+01:00",
        "2019-03-30T17:00:00.000+01:00",
        "2019-03-30T18:00:00.000+01:00",
        "2019-03-30T19:00:00.000+01:00",
        "2019-03-30T20:00:00.000+01:00",
        "2019-03-30T21:00:00.000+01:00",
        "2019-03-30T22:00:00.000+01:00",
        "2019-03-30T23:00:00.000+01:00",
        "2019-03-31T00:00:00.000+01:00",
        "2019-03-31T01:00:00.000+01:00",
        "2019-03-31T03:00:00.000+02:00",
        "2019-03-31T04:00:00.000+02:00",
        "2019-03-31T05:00:00.000+02:00",
        "2019-03-31T06:00:00.000+02:00",
        "2019-03-31T07:00:00.000+02:00",
        "2019-03-31T08:00:00.000+02:00",
        "2019-03-31T09:00:00.000+02:00",
        "2019-03-31T10:00:00.000+02:00",
        "2019-03-31T11:00:00.000+02:00",
        "2019-03-31T12:00:00.000+02:00",
        "2019-03-31T13:00:00.000+02:00",
        "2019-03-31T14:00:00.000+02:00",
    ]);

    await setScale(4);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-03-31", stopDate: "2019-04-07" });
    expect(getGridInfo()).toEqual([
        "2019-03-31T00:00:00.000+01:00",
        "2019-04-01T00:00:00.000+02:00",
        "2019-04-02T00:00:00.000+02:00",
        "2019-04-03T00:00:00.000+02:00",
        "2019-04-04T00:00:00.000+02:00",
        "2019-04-05T00:00:00.000+02:00",
        "2019-04-06T00:00:00.000+02:00",
        "2019-04-07T00:00:00.000+02:00",
    ]);

    await setScale(2);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-03-01", stopDate: "2019-04-01" });
    expect(getGridInfo()).toEqual([
        "2019-03-02T00:00:00.000+01:00",
        "2019-03-03T00:00:00.000+01:00",
        "2019-03-04T00:00:00.000+01:00",
        "2019-03-05T00:00:00.000+01:00",
        "2019-03-06T00:00:00.000+01:00",
        "2019-03-07T00:00:00.000+01:00",
        "2019-03-08T00:00:00.000+01:00",
        "2019-03-09T00:00:00.000+01:00",
        "2019-03-10T00:00:00.000+01:00",
        "2019-03-11T00:00:00.000+01:00",
        "2019-03-12T00:00:00.000+01:00",
        "2019-03-13T00:00:00.000+01:00",
        "2019-03-14T00:00:00.000+01:00",
        "2019-03-15T00:00:00.000+01:00",
        "2019-03-16T00:00:00.000+01:00",
        "2019-03-17T00:00:00.000+01:00",
        "2019-03-18T00:00:00.000+01:00",
        "2019-03-19T00:00:00.000+01:00",
        "2019-03-20T00:00:00.000+01:00",
        "2019-03-21T00:00:00.000+01:00",
        "2019-03-22T00:00:00.000+01:00",
        "2019-03-23T00:00:00.000+01:00",
        "2019-03-24T00:00:00.000+01:00",
        "2019-03-25T00:00:00.000+01:00",
        "2019-03-26T00:00:00.000+01:00",
        "2019-03-27T00:00:00.000+01:00",
        "2019-03-28T00:00:00.000+01:00",
        "2019-03-29T00:00:00.000+01:00",
        "2019-03-30T00:00:00.000+01:00",
        "2019-03-31T00:00:00.000+01:00",
        "2019-04-01T00:00:00.000+02:00",
    ]);

    await setScale(0);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-01-01", stopDate: "2020-01-01" });
    expect(getGridInfo()).toEqual([
        "2019-01-01T00:00:00.000+01:00",
        "2019-02-01T00:00:00.000+01:00",
        "2019-03-01T00:00:00.000+01:00",
        "2019-04-01T00:00:00.000+02:00",
        "2019-05-01T00:00:00.000+02:00",
        "2019-06-01T00:00:00.000+02:00",
        "2019-07-01T00:00:00.000+02:00",
        "2019-08-01T00:00:00.000+02:00",
        "2019-09-01T00:00:00.000+02:00",
        "2019-10-01T00:00:00.000+02:00",
        "2019-11-01T00:00:00.000+01:00",
        "2019-12-01T00:00:00.000+01:00",
        "2020-01-01T00:00:00.000+01:00",
    ]);
});

test("date grid and dst summerToWinter (1 cell part)", async () => {
    let renderer;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        },
    });

    mockTimeZone("Europe/Brussels");
    Tasks._records = [];

    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day" precision="{'day':'hour:full', 'week':'day:full', 'month':'day:full', 'year':'month:full' }"/>`,
        domain: [["id", "=", 8]],
        context: {
            initialDate: `${DST_DATES.summerToWinter.before} 08:00:00`,
        },
    });

    function getGridInfo() {
        return renderer.subColumns.map(({ start }) => start.toString());
    }
    expect(getGridInfo()).toEqual([
        "2019-10-26T00:00:00.000+02:00",
        "2019-10-26T01:00:00.000+02:00",
        "2019-10-26T02:00:00.000+02:00",
        "2019-10-26T03:00:00.000+02:00",
        "2019-10-26T04:00:00.000+02:00",
        "2019-10-26T05:00:00.000+02:00",
        "2019-10-26T06:00:00.000+02:00",
        "2019-10-26T07:00:00.000+02:00",
        "2019-10-26T08:00:00.000+02:00",
        "2019-10-26T09:00:00.000+02:00",
        "2019-10-26T10:00:00.000+02:00",
        "2019-10-26T11:00:00.000+02:00",
        "2019-10-26T12:00:00.000+02:00",
        "2019-10-26T13:00:00.000+02:00",
        "2019-10-26T14:00:00.000+02:00",
        "2019-10-26T15:00:00.000+02:00",
        "2019-10-26T16:00:00.000+02:00",
        "2019-10-26T17:00:00.000+02:00",
        "2019-10-26T18:00:00.000+02:00",
        "2019-10-26T19:00:00.000+02:00",
        "2019-10-26T20:00:00.000+02:00",
        "2019-10-26T21:00:00.000+02:00",
        "2019-10-26T22:00:00.000+02:00",
        "2019-10-26T23:00:00.000+02:00",
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-27T01:00:00.000+02:00",
        "2019-10-27T02:00:00.000+02:00",
        "2019-10-27T02:00:00.000+01:00",
        "2019-10-27T03:00:00.000+01:00",
        "2019-10-27T04:00:00.000+01:00",
        "2019-10-27T05:00:00.000+01:00",
        "2019-10-27T06:00:00.000+01:00",
        "2019-10-27T07:00:00.000+01:00",
        "2019-10-27T08:00:00.000+01:00",
        "2019-10-27T09:00:00.000+01:00",
        "2019-10-27T10:00:00.000+01:00",
        "2019-10-27T11:00:00.000+01:00",
        "2019-10-27T12:00:00.000+01:00",
    ]);

    await setScale(4);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-10-27", stopDate: "2019-11-03" });
    expect(getGridInfo()).toEqual([
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-28T00:00:00.000+01:00",
        "2019-10-29T00:00:00.000+01:00",
        "2019-10-30T00:00:00.000+01:00",
        "2019-10-31T00:00:00.000+01:00",
        "2019-11-01T00:00:00.000+01:00",
        "2019-11-02T00:00:00.000+01:00",
        "2019-11-03T00:00:00.000+01:00",
    ]);

    await setScale(2);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-10-01", stopDate: "2019-11-01" });
    expect(getGridInfo()).toEqual([
        "2019-10-02T00:00:00.000+02:00",
        "2019-10-03T00:00:00.000+02:00",
        "2019-10-04T00:00:00.000+02:00",
        "2019-10-05T00:00:00.000+02:00",
        "2019-10-06T00:00:00.000+02:00",
        "2019-10-07T00:00:00.000+02:00",
        "2019-10-08T00:00:00.000+02:00",
        "2019-10-09T00:00:00.000+02:00",
        "2019-10-10T00:00:00.000+02:00",
        "2019-10-11T00:00:00.000+02:00",
        "2019-10-12T00:00:00.000+02:00",
        "2019-10-13T00:00:00.000+02:00",
        "2019-10-14T00:00:00.000+02:00",
        "2019-10-15T00:00:00.000+02:00",
        "2019-10-16T00:00:00.000+02:00",
        "2019-10-17T00:00:00.000+02:00",
        "2019-10-18T00:00:00.000+02:00",
        "2019-10-19T00:00:00.000+02:00",
        "2019-10-20T00:00:00.000+02:00",
        "2019-10-21T00:00:00.000+02:00",
        "2019-10-22T00:00:00.000+02:00",
        "2019-10-23T00:00:00.000+02:00",
        "2019-10-24T00:00:00.000+02:00",
        "2019-10-25T00:00:00.000+02:00",
        "2019-10-26T00:00:00.000+02:00",
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-28T00:00:00.000+01:00",
        "2019-10-29T00:00:00.000+01:00",
        "2019-10-30T00:00:00.000+01:00",
        "2019-10-31T00:00:00.000+01:00",
        "2019-11-01T00:00:00.000+01:00",
    ]);

    await setScale(0);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-01-01", stopDate: "2020-01-01" });
    expect(getGridInfo()).toEqual([
        "2019-01-01T00:00:00.000+01:00",
        "2019-02-01T00:00:00.000+01:00",
        "2019-03-01T00:00:00.000+01:00",
        "2019-04-01T00:00:00.000+02:00",
        "2019-05-01T00:00:00.000+02:00",
        "2019-06-01T00:00:00.000+02:00",
        "2019-07-01T00:00:00.000+02:00",
        "2019-08-01T00:00:00.000+02:00",
        "2019-09-01T00:00:00.000+02:00",
        "2019-10-01T00:00:00.000+02:00",
        "2019-11-01T00:00:00.000+01:00",
        "2019-12-01T00:00:00.000+01:00",
        "2020-01-01T00:00:00.000+01:00",
    ]);
});

test("date grid and dst winterToSummer (2 cell part)", async () => {
    let renderer;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        },
    });

    mockTimeZone("Europe/Brussels");
    Tasks._records = [];

    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day" precision="{'day':'hour:half', 'week':'day:half', 'month':'day:half'}"/>`,
        domain: [["id", "=", 8]],
        context: {
            initialDate: `${DST_DATES.winterToSummer.before} 08:00:00`,
        },
    });

    function getGridInfo() {
        return renderer.subColumns.map(({ start }) => start.toString());
    }
    expect(getGridInfo()).toEqual([
        "2019-03-30T00:00:00.000+01:00",
        "2019-03-30T00:30:00.000+01:00",
        "2019-03-30T01:00:00.000+01:00",
        "2019-03-30T01:30:00.000+01:00",
        "2019-03-30T02:00:00.000+01:00",
        "2019-03-30T02:30:00.000+01:00",
        "2019-03-30T03:00:00.000+01:00",
        "2019-03-30T03:30:00.000+01:00",
        "2019-03-30T04:00:00.000+01:00",
        "2019-03-30T04:30:00.000+01:00",
        "2019-03-30T05:00:00.000+01:00",
        "2019-03-30T05:30:00.000+01:00",
        "2019-03-30T06:00:00.000+01:00",
        "2019-03-30T06:30:00.000+01:00",
        "2019-03-30T07:00:00.000+01:00",
        "2019-03-30T07:30:00.000+01:00",
        "2019-03-30T08:00:00.000+01:00",
        "2019-03-30T08:30:00.000+01:00",
        "2019-03-30T09:00:00.000+01:00",
        "2019-03-30T09:30:00.000+01:00",
        "2019-03-30T10:00:00.000+01:00",
        "2019-03-30T10:30:00.000+01:00",
        "2019-03-30T11:00:00.000+01:00",
        "2019-03-30T11:30:00.000+01:00",
        "2019-03-30T12:00:00.000+01:00",
        "2019-03-30T12:30:00.000+01:00",
        "2019-03-30T13:00:00.000+01:00",
        "2019-03-30T13:30:00.000+01:00",
        "2019-03-30T14:00:00.000+01:00",
        "2019-03-30T14:30:00.000+01:00",
        "2019-03-30T15:00:00.000+01:00",
        "2019-03-30T15:30:00.000+01:00",
        "2019-03-30T16:00:00.000+01:00",
        "2019-03-30T16:30:00.000+01:00",
        "2019-03-30T17:00:00.000+01:00",
        "2019-03-30T17:30:00.000+01:00",
        "2019-03-30T18:00:00.000+01:00",
        "2019-03-30T18:30:00.000+01:00",
        "2019-03-30T19:00:00.000+01:00",
        "2019-03-30T19:30:00.000+01:00",
        "2019-03-30T20:00:00.000+01:00",
        "2019-03-30T20:30:00.000+01:00",
        "2019-03-30T21:00:00.000+01:00",
        "2019-03-30T21:30:00.000+01:00",
        "2019-03-30T22:00:00.000+01:00",
        "2019-03-30T22:30:00.000+01:00",
        "2019-03-30T23:00:00.000+01:00",
        "2019-03-30T23:30:00.000+01:00",
        "2019-03-31T00:00:00.000+01:00",
        "2019-03-31T00:30:00.000+01:00",
        "2019-03-31T01:00:00.000+01:00",
        "2019-03-31T01:30:00.000+01:00",
        "2019-03-31T03:00:00.000+02:00",
        "2019-03-31T03:30:00.000+02:00",
        "2019-03-31T04:00:00.000+02:00",
        "2019-03-31T04:30:00.000+02:00",
        "2019-03-31T05:00:00.000+02:00",
        "2019-03-31T05:30:00.000+02:00",
        "2019-03-31T06:00:00.000+02:00",
        "2019-03-31T06:30:00.000+02:00",
        "2019-03-31T07:00:00.000+02:00",
        "2019-03-31T07:30:00.000+02:00",
        "2019-03-31T08:00:00.000+02:00",
        "2019-03-31T08:30:00.000+02:00",
        "2019-03-31T09:00:00.000+02:00",
        "2019-03-31T09:30:00.000+02:00",
        "2019-03-31T10:00:00.000+02:00",
        "2019-03-31T10:30:00.000+02:00",
        "2019-03-31T11:00:00.000+02:00",
        "2019-03-31T11:30:00.000+02:00",
        "2019-03-31T12:00:00.000+02:00",
        "2019-03-31T12:30:00.000+02:00",
        "2019-03-31T13:00:00.000+02:00",
        "2019-03-31T13:30:00.000+02:00",
        "2019-03-31T14:00:00.000+02:00",
        "2019-03-31T14:30:00.000+02:00",
    ]);

    await setScale(4);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-03-31", stopDate: "2019-04-07" });
    expect(getGridInfo()).toEqual([
        "2019-03-31T00:00:00.000+01:00",
        "2019-03-31T12:00:00.000+02:00",
        "2019-04-01T00:00:00.000+02:00",
        "2019-04-01T12:00:00.000+02:00",
        "2019-04-02T00:00:00.000+02:00",
        "2019-04-02T12:00:00.000+02:00",
        "2019-04-03T00:00:00.000+02:00",
        "2019-04-03T12:00:00.000+02:00",
        "2019-04-04T00:00:00.000+02:00",
        "2019-04-04T12:00:00.000+02:00",
        "2019-04-05T00:00:00.000+02:00",
        "2019-04-05T12:00:00.000+02:00",
        "2019-04-06T00:00:00.000+02:00",
        "2019-04-06T12:00:00.000+02:00",
        "2019-04-07T00:00:00.000+02:00",
        "2019-04-07T12:00:00.000+02:00",
    ]);

    await setScale(2);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-03-01", stopDate: "2019-04-01" });
    expect(getGridInfo()).toEqual([
        "2019-03-02T00:00:00.000+01:00",
        "2019-03-02T12:00:00.000+01:00",
        "2019-03-03T00:00:00.000+01:00",
        "2019-03-03T12:00:00.000+01:00",
        "2019-03-04T00:00:00.000+01:00",
        "2019-03-04T12:00:00.000+01:00",
        "2019-03-05T00:00:00.000+01:00",
        "2019-03-05T12:00:00.000+01:00",
        "2019-03-06T00:00:00.000+01:00",
        "2019-03-06T12:00:00.000+01:00",
        "2019-03-07T00:00:00.000+01:00",
        "2019-03-07T12:00:00.000+01:00",
        "2019-03-08T00:00:00.000+01:00",
        "2019-03-08T12:00:00.000+01:00",
        "2019-03-09T00:00:00.000+01:00",
        "2019-03-09T12:00:00.000+01:00",
        "2019-03-10T00:00:00.000+01:00",
        "2019-03-10T12:00:00.000+01:00",
        "2019-03-11T00:00:00.000+01:00",
        "2019-03-11T12:00:00.000+01:00",
        "2019-03-12T00:00:00.000+01:00",
        "2019-03-12T12:00:00.000+01:00",
        "2019-03-13T00:00:00.000+01:00",
        "2019-03-13T12:00:00.000+01:00",
        "2019-03-14T00:00:00.000+01:00",
        "2019-03-14T12:00:00.000+01:00",
        "2019-03-15T00:00:00.000+01:00",
        "2019-03-15T12:00:00.000+01:00",
        "2019-03-16T00:00:00.000+01:00",
        "2019-03-16T12:00:00.000+01:00",
        "2019-03-17T00:00:00.000+01:00",
        "2019-03-17T12:00:00.000+01:00",
        "2019-03-18T00:00:00.000+01:00",
        "2019-03-18T12:00:00.000+01:00",
        "2019-03-19T00:00:00.000+01:00",
        "2019-03-19T12:00:00.000+01:00",
        "2019-03-20T00:00:00.000+01:00",
        "2019-03-20T12:00:00.000+01:00",
        "2019-03-21T00:00:00.000+01:00",
        "2019-03-21T12:00:00.000+01:00",
        "2019-03-22T00:00:00.000+01:00",
        "2019-03-22T12:00:00.000+01:00",
        "2019-03-23T00:00:00.000+01:00",
        "2019-03-23T12:00:00.000+01:00",
        "2019-03-24T00:00:00.000+01:00",
        "2019-03-24T12:00:00.000+01:00",
        "2019-03-25T00:00:00.000+01:00",
        "2019-03-25T12:00:00.000+01:00",
        "2019-03-26T00:00:00.000+01:00",
        "2019-03-26T12:00:00.000+01:00",
        "2019-03-27T00:00:00.000+01:00",
        "2019-03-27T12:00:00.000+01:00",
        "2019-03-28T00:00:00.000+01:00",
        "2019-03-28T12:00:00.000+01:00",
        "2019-03-29T00:00:00.000+01:00",
        "2019-03-29T12:00:00.000+01:00",
        "2019-03-30T00:00:00.000+01:00",
        "2019-03-30T12:00:00.000+01:00",
        "2019-03-31T00:00:00.000+01:00",
        "2019-03-31T12:00:00.000+02:00",
        "2019-04-01T00:00:00.000+02:00",
        "2019-04-01T12:00:00.000+02:00",
    ]);
});

test("date grid and dst summerToWinter (2 cell part)", async () => {
    let renderer;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        },
    });

    mockTimeZone("Europe/Brussels");
    Tasks._records = [];

    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day" precision="{'day':'hour:half', 'week':'day:half', 'month':'day:half'}"/>`,
        context: {
            initialDate: `${DST_DATES.summerToWinter.before} 08:00:00`,
        },
    });

    function getGridInfo() {
        return renderer.subColumns.map(({ start }) => start.toString());
    }
    expect(getGridInfo()).toEqual([
        "2019-10-26T00:00:00.000+02:00",
        "2019-10-26T00:30:00.000+02:00",
        "2019-10-26T01:00:00.000+02:00",
        "2019-10-26T01:30:00.000+02:00",
        "2019-10-26T02:00:00.000+02:00",
        "2019-10-26T02:30:00.000+02:00",
        "2019-10-26T03:00:00.000+02:00",
        "2019-10-26T03:30:00.000+02:00",
        "2019-10-26T04:00:00.000+02:00",
        "2019-10-26T04:30:00.000+02:00",
        "2019-10-26T05:00:00.000+02:00",
        "2019-10-26T05:30:00.000+02:00",
        "2019-10-26T06:00:00.000+02:00",
        "2019-10-26T06:30:00.000+02:00",
        "2019-10-26T07:00:00.000+02:00",
        "2019-10-26T07:30:00.000+02:00",
        "2019-10-26T08:00:00.000+02:00",
        "2019-10-26T08:30:00.000+02:00",
        "2019-10-26T09:00:00.000+02:00",
        "2019-10-26T09:30:00.000+02:00",
        "2019-10-26T10:00:00.000+02:00",
        "2019-10-26T10:30:00.000+02:00",
        "2019-10-26T11:00:00.000+02:00",
        "2019-10-26T11:30:00.000+02:00",
        "2019-10-26T12:00:00.000+02:00",
        "2019-10-26T12:30:00.000+02:00",
        "2019-10-26T13:00:00.000+02:00",
        "2019-10-26T13:30:00.000+02:00",
        "2019-10-26T14:00:00.000+02:00",
        "2019-10-26T14:30:00.000+02:00",
        "2019-10-26T15:00:00.000+02:00",
        "2019-10-26T15:30:00.000+02:00",
        "2019-10-26T16:00:00.000+02:00",
        "2019-10-26T16:30:00.000+02:00",
        "2019-10-26T17:00:00.000+02:00",
        "2019-10-26T17:30:00.000+02:00",
        "2019-10-26T18:00:00.000+02:00",
        "2019-10-26T18:30:00.000+02:00",
        "2019-10-26T19:00:00.000+02:00",
        "2019-10-26T19:30:00.000+02:00",
        "2019-10-26T20:00:00.000+02:00",
        "2019-10-26T20:30:00.000+02:00",
        "2019-10-26T21:00:00.000+02:00",
        "2019-10-26T21:30:00.000+02:00",
        "2019-10-26T22:00:00.000+02:00",
        "2019-10-26T22:30:00.000+02:00",
        "2019-10-26T23:00:00.000+02:00",
        "2019-10-26T23:30:00.000+02:00",
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-27T00:30:00.000+02:00",
        "2019-10-27T01:00:00.000+02:00",
        "2019-10-27T01:30:00.000+02:00",
        "2019-10-27T02:00:00.000+02:00",
        "2019-10-27T02:30:00.000+02:00",
        "2019-10-27T02:00:00.000+01:00",
        "2019-10-27T02:30:00.000+01:00",
        "2019-10-27T03:00:00.000+01:00",
        "2019-10-27T03:30:00.000+01:00",
        "2019-10-27T04:00:00.000+01:00",
        "2019-10-27T04:30:00.000+01:00",
        "2019-10-27T05:00:00.000+01:00",
        "2019-10-27T05:30:00.000+01:00",
        "2019-10-27T06:00:00.000+01:00",
        "2019-10-27T06:30:00.000+01:00",
        "2019-10-27T07:00:00.000+01:00",
        "2019-10-27T07:30:00.000+01:00",
        "2019-10-27T08:00:00.000+01:00",
        "2019-10-27T08:30:00.000+01:00",
        "2019-10-27T09:00:00.000+01:00",
        "2019-10-27T09:30:00.000+01:00",
        "2019-10-27T10:00:00.000+01:00",
        "2019-10-27T10:30:00.000+01:00",
        "2019-10-27T11:00:00.000+01:00",
        "2019-10-27T11:30:00.000+01:00",
        "2019-10-27T12:00:00.000+01:00",
        "2019-10-27T12:30:00.000+01:00",
    ]);

    await setScale(4);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-10-27", stopDate: "2019-11-03" });
    expect(getGridInfo()).toEqual([
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-27T12:00:00.000+01:00",
        "2019-10-28T00:00:00.000+01:00",
        "2019-10-28T12:00:00.000+01:00",
        "2019-10-29T00:00:00.000+01:00",
        "2019-10-29T12:00:00.000+01:00",
        "2019-10-30T00:00:00.000+01:00",
        "2019-10-30T12:00:00.000+01:00",
        "2019-10-31T00:00:00.000+01:00",
        "2019-10-31T12:00:00.000+01:00",
        "2019-11-01T00:00:00.000+01:00",
        "2019-11-01T12:00:00.000+01:00",
        "2019-11-02T00:00:00.000+01:00",
        "2019-11-02T12:00:00.000+01:00",
        "2019-11-03T00:00:00.000+01:00",
        "2019-11-03T12:00:00.000+01:00",
    ]);

    await setScale(2);
    await ganttControlsChanges();
    await selectGanttRange({ startDate: "2019-10-01", stopDate: "2019-11-01" });
    expect(getGridInfo()).toEqual([
        "2019-10-02T00:00:00.000+02:00",
        "2019-10-02T12:00:00.000+02:00",
        "2019-10-03T00:00:00.000+02:00",
        "2019-10-03T12:00:00.000+02:00",
        "2019-10-04T00:00:00.000+02:00",
        "2019-10-04T12:00:00.000+02:00",
        "2019-10-05T00:00:00.000+02:00",
        "2019-10-05T12:00:00.000+02:00",
        "2019-10-06T00:00:00.000+02:00",
        "2019-10-06T12:00:00.000+02:00",
        "2019-10-07T00:00:00.000+02:00",
        "2019-10-07T12:00:00.000+02:00",
        "2019-10-08T00:00:00.000+02:00",
        "2019-10-08T12:00:00.000+02:00",
        "2019-10-09T00:00:00.000+02:00",
        "2019-10-09T12:00:00.000+02:00",
        "2019-10-10T00:00:00.000+02:00",
        "2019-10-10T12:00:00.000+02:00",
        "2019-10-11T00:00:00.000+02:00",
        "2019-10-11T12:00:00.000+02:00",
        "2019-10-12T00:00:00.000+02:00",
        "2019-10-12T12:00:00.000+02:00",
        "2019-10-13T00:00:00.000+02:00",
        "2019-10-13T12:00:00.000+02:00",
        "2019-10-14T00:00:00.000+02:00",
        "2019-10-14T12:00:00.000+02:00",
        "2019-10-15T00:00:00.000+02:00",
        "2019-10-15T12:00:00.000+02:00",
        "2019-10-16T00:00:00.000+02:00",
        "2019-10-16T12:00:00.000+02:00",
        "2019-10-17T00:00:00.000+02:00",
        "2019-10-17T12:00:00.000+02:00",
        "2019-10-18T00:00:00.000+02:00",
        "2019-10-18T12:00:00.000+02:00",
        "2019-10-19T00:00:00.000+02:00",
        "2019-10-19T12:00:00.000+02:00",
        "2019-10-20T00:00:00.000+02:00",
        "2019-10-20T12:00:00.000+02:00",
        "2019-10-21T00:00:00.000+02:00",
        "2019-10-21T12:00:00.000+02:00",
        "2019-10-22T00:00:00.000+02:00",
        "2019-10-22T12:00:00.000+02:00",
        "2019-10-23T00:00:00.000+02:00",
        "2019-10-23T12:00:00.000+02:00",
        "2019-10-24T00:00:00.000+02:00",
        "2019-10-24T12:00:00.000+02:00",
        "2019-10-25T00:00:00.000+02:00",
        "2019-10-25T12:00:00.000+02:00",
        "2019-10-26T00:00:00.000+02:00",
        "2019-10-26T12:00:00.000+02:00",
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-27T12:00:00.000+01:00",
        "2019-10-28T00:00:00.000+01:00",
        "2019-10-28T12:00:00.000+01:00",
        "2019-10-29T00:00:00.000+01:00",
        "2019-10-29T12:00:00.000+01:00",
        "2019-10-30T00:00:00.000+01:00",
        "2019-10-30T12:00:00.000+01:00",
        "2019-10-31T00:00:00.000+01:00",
        "2019-10-31T12:00:00.000+01:00",
        "2019-11-01T00:00:00.000+01:00",
        "2019-11-01T12:00:00.000+01:00",
    ]);
});

test("groups_limit attribute (no groupBy)", async () => {
    onRpc(({ method, kwargs }) => {
        expect.step(method);
        if (kwargs.limit) {
            expect.step(`with limit ${kwargs.limit}`);
        }
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" groups_limit="2"/>`,
    });
    expect(".o_gantt_view .o_control_panel .o_pager").toHaveCount(0); // only one group here!
    expect.verifySteps(["get_views", "get_gantt_data", "with limit 2"]);
    const { rows } = getGridContent();
    expect(rows).toEqual([
        {
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 04 (1/2) December 2018",
                    level: 0,
                    title: "Task 5",
                },
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    level: 1,
                    title: "Task 1",
                },
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    level: 2,
                    title: "Task 4",
                },
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    level: 2,
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

test("groups_limit attribute (one groupBy)", async () => {
    onRpc(({ method, kwargs }) => {
        expect.step(method);
        if (kwargs.limit) {
            expect.step(`with limit ${kwargs.limit}`);
            expect.step(`with offset ${kwargs.offset}`);
        }
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" groups_limit="2"/>`,
        groupBy: ["stage_id"],
    });
    expect(".o_gantt_view .o_control_panel .o_pager").toHaveCount(1);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("4");
    let rows = getGridContent().rows;
    expect(rows).toEqual([
        {
            title: "todo",
        },
        {
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    level: 0,
                    title: "Task 1",
                },
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    level: 1,
                    title: "Task 7",
                },
            ],
            title: "in_progress",
        },
    ]);
    expect.verifySteps(["get_views", "get_gantt_data", "with limit 2", "with offset 0"]);

    await pagerNext();
    expect(".o_pager_value").toHaveText("3-4");
    expect(".o_pager_limit").toHaveText("4");
    rows = getGridContent().rows;
    expect(rows).toEqual([
        {
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "done",
        },
        {
            pills: [
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    level: 0,
                    title: "Task 4",
                },
                {
                    colSpan: "27 December 2018 -> 03 (1/2) January 2019",
                    level: 0,
                    title: "Task 3",
                },
            ],
            title: "cancel",
        },
    ]);
    expect.verifySteps(["get_gantt_data", "with limit 2", "with offset 2"]);
});

test("groups_limit attribute (two groupBys)", async () => {
    onRpc(({ method, kwargs }) => {
        expect.step(method);
        if (kwargs.limit) {
            expect.step(`with limit ${kwargs.limit}`);
            expect.step(`with offset ${kwargs.offset}`);
        }
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" groups_limit="2"/>`,
        groupBy: ["stage_id", "project_id"],
    });
    expect(".o_gantt_view .o_control_panel .o_pager").toHaveCount(1);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("5");
    let rows = getGridContent().rows;
    expect(rows).toEqual([
        {
            isGroup: true,
            title: "todo",
        },
        {
            title: "Project 2",
        },
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    title: "1",
                },
            ],
            title: "in_progress",
        },
        {
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    level: 0,
                    title: "Task 1",
                },
            ],
            title: "Project 1",
        },
    ]);
    expect.verifySteps(["get_views", "get_gantt_data", "with limit 2", "with offset 0"]);

    await pagerNext();
    expect(".o_pager_value").toHaveText("3-4");
    expect(".o_pager_limit").toHaveText("5");
    rows = getGridContent().rows;
    expect(rows).toEqual([
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    title: "1",
                },
            ],
            title: "in_progress",
        },
        {
            pills: [
                {
                    colSpan: "20 (1/2) December 2018 -> 20 December 2018",
                    level: 0,
                    title: "Task 7",
                },
            ],
            title: "Project 2",
        },
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    title: "1",
                },
            ],
            title: "done",
        },
        {
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "Project 1",
        },
    ]);
    expect.verifySteps(["get_gantt_data", "with limit 2", "with offset 2"]);

    await pagerNext();
    expect(".o_pager_value").toHaveText("5-5");
    expect(".o_pager_limit").toHaveText("5");
    rows = getGridContent().rows;
    expect(rows).toEqual([
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    title: "1",
                },
                {
                    colSpan: "27 December 2018 -> 03 (1/2) January 2019",
                    title: "1",
                },
            ],
            title: "cancel",
        },
        {
            pills: [
                {
                    colSpan: "20 December 2018 -> 20 (1/2) December 2018",
                    level: 0,
                    title: "Task 4",
                },
                {
                    colSpan: "27 December 2018 -> 03 (1/2) January 2019",
                    level: 0,
                    title: "Task 3",
                },
            ],
            title: "Project 1",
        },
    ]);
    expect.verifySteps(["get_gantt_data", "with limit 2", "with offset 4"]);
});

test("groups_limit attribute in sample mode (no groupBy)", async () => {
    onRpc(({ method, kwargs }) => {
        expect.step(method);
        if (kwargs.limit) {
            expect.step(`with limit ${kwargs.limit}`);
        }
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" groups_limit="2" sample="1"/>`,
        domain: Domain.FALSE.toList(),
    });
    expect(".o_gantt_view .o_control_panel .o_pager").toHaveCount(0); // only one group here!
    expect.verifySteps(["get_views", "get_gantt_data", "with limit 2"]);
});

test("groups_limit attribute in sample mode (one groupBy)", async () => {
    onRpc(({ method, kwargs }) => {
        expect.step(method);
        if (kwargs.limit) {
            expect.step(`with limit ${kwargs.limit}`);
            expect.step(`with offset ${kwargs.offset}`);
        }
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" groups_limit="2" sample="1"/>`,
        domain: Domain.FALSE.toList(),
        groupBy: ["stage_id"],
    });
    expect(".o_gantt_view .o_control_panel .o_pager").toHaveCount(1);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("2");
    expect(".o_gantt_row_title").toHaveCount(2);
    expect.verifySteps(["get_views", "get_gantt_data", "with limit 2", "with offset 0"]);
});

test("groups_limit attribute in sample mode (two groupBys)", async () => {
    onRpc(({ method, kwargs }) => {
        expect.step(method);
        if (kwargs.limit) {
            expect.step(`with limit ${kwargs.limit}`);
            expect.step(`with offset ${kwargs.offset}`);
        }
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" groups_limit="2" sample="1"/>`,
        domain: Domain.FALSE.toList(),
        groupBy: ["stage_id", "project_id"],
    });
    expect(".o_gantt_view .o_control_panel .o_pager").toHaveCount(1);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("2");
    expect.verifySteps(["get_views", "get_gantt_data", "with limit 2", "with offset 0"]);
});

test("context in action should not override context added by the gantt view", async () => {
    Tasks._views.form = `
        <form>
            <field name="name"/>
            <field name="user_id"/>
            <field name="start"/>
            <field name="stop"/>
        </form>
    `;
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_group_by="user_id" plan="false"/>`,
        context: {
            gantt_date: "2018-11-30",
            gantt_scale: "month",
            default_user_id: false,
        },
    });
    await hoverGridCell("11 December 2018");
    await clickCell("11 December 2018");
    expect(".modal .o_field_many2one[name=user_id]").toHaveCount(1);
    expect(".modal .o_field_many2one[name=user_id] input").toHaveValue("User 1");
});

test("The date shouldn't appear in the title if the pill is displayed on 2 days", async () => {
    mockDate("2024-01-01T08:00:00", +0);

    Tasks._records.push(
        {
            id: 9,
            name: "Task 9",
            allocated_hours: 4,
            start: "2024-01-01 16:00:00",
            stop: "2024-01-02 01:00:00",
        },
        {
            id: 10,
            name: "Task 10",
            allocated_hours: 4,
            start: "2024-01-02 16:00:00",
            stop: "2024-01-03 02:00:00",
        },
        {
            id: 11,
            name: "Task 11",
            allocated_hours: 4,
            start: "2024-01-03 16:00:00",
            stop: "2024-01-04 03:00:00",
        }
    );
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start"
                          date_stop="stop"
                          pill_label="True"
                          default_scale="week"
                          scales="week"
                          precision="{'week': 'day:full'}"
                    >
                    <field name="allocated_hours"/>
                </gantt>`,
    });
    expect(".o_gantt_pill").toHaveCount(3, { message: "should have 3 pills in the gantt view" });
    expect(queryAllTexts(".o_gantt_pill_title")).toEqual([
        "Task 9",
        "Task 10",
        "Task 11",
    ]);
});

test("Gantt view should not crash when opening on a DST transition day (Asia/Beirut)", async () => {
    // Beirut (Asia/Beirut) springs forward at midnight on the last Sunday of March,
    // making that day only 23 hours long. diffColumn() used to return a float (e.g.
    // 6.958 days for a 7-day week) because luxon's .diff() works in absolute time.
    // Array(6.958) throws RangeError: Invalid array length, crashing the gantt view.
    mockTimeZone("Asia/Beirut");
    Tasks._records = [
        {
            id: 1,
            name: "Beirut DST Task",
            start: `${DST_DATES.winterToSummer.before} 08:00:00`,
            stop: `${DST_DATES.winterToSummer.after} 17:00:00`,
        },
    ];
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="week"/>`,
        context: {
            initialDate: `${DST_DATES.winterToSummer.before} 08:00:00`,
        },
    });
    const { columnHeaders, rows } = getGridContent();
    expect(columnHeaders.length).toBeGreaterThan(0);
    expect(rows[0].pills).toHaveLength(1);
});
