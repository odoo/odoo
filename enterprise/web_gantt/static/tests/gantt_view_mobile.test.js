import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { contains, getService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { Domain } from "@web/core/domain";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { WebClient } from "@web/webclient/webclient";
import { Tasks, defineGanttModels } from "./gantt_mock_models";
import {
    CLASSES,
    SELECTORS,
    getActiveScale,
    getGridContent,
    mountGanttView,
} from "./web_gantt_test_helpers";

defineGanttModels();

describe.current.tags("mobile");

beforeEach(() => mockDate("2018-12-20T08:00:00", +1));

test("empty ungrouped gantt rendering", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" />`,
        domain: [["id", "=", 0]],
    });
    const { viewTitle, range, columnHeaders, rows } = getGridContent();
    expect(viewTitle).toBe(null);
    expect(range).toBe("12/01/2018 -> 02/28/2019");
    expect(columnHeaders).toHaveLength(10);
    expect(columnHeaders.at(0).title).toBe("15");
    expect(columnHeaders.at(-1).title).toBe("24");
    expect(rows).toEqual([{}]);
    expect(SELECTORS.noContentHelper).toHaveCount(0);
});

test("ungrouped gantt rendering", async () => {
    const task2 = Tasks._records[1];
    const startDateLocalString = deserializeDateTime(task2.start).toFormat("f");
    const stopDateLocalString = deserializeDateTime(task2.stop).toFormat("f");
    Tasks._views.gantt = `<gantt date_start="start" date_stop="stop"/>`;

    onRpc("get_gantt_data", ({ model }) => expect.step(model));
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [[false, "gantt"]],
    });
    expect.verifySteps(["tasks"]);
    await animationFrame();

    const { viewTitle, range, columnHeaders, rows } = getGridContent();
    expect(viewTitle).toBe(null);
    expect(range).toBe("12/01/2018 -> 02/28/2019");
    expect(columnHeaders).toHaveLength(10);
    expect(columnHeaders.at(0).title).toBe("15");
    expect(columnHeaders.at(-1).title).toBe("24");
    expect(getActiveScale()).toBe(2);
    expect(SELECTORS.expandCollapseButtons).not.toHaveCount();
    expect(rows).toEqual([
        {
            pills: [
                { title: "Task 1", level: 1, colSpan: "Out of bounds (1)  -> Out of bounds (63) " },
                {
                    title: "Task 2",
                    level: 0,
                    colSpan: "17 (1/2) Dec 2018 -> 22 (1/2) Dec 2018",
                },
                {
                    title: "Task 4",
                    level: 2,
                    colSpan: "20 Dec 2018 -> 20 (1/2) Dec 2018",
                },
                {
                    title: "Task 7",
                    level: 2,
                    colSpan: "20 (1/2) Dec 2018 -> 20 Dec 2018",
                },
            ],
        },
    ]);

    // test popover and local timezone
    expect(`.o_popover`).toHaveCount(0);
    const task2Pill = queryAll(SELECTORS.pill)[1];
    expect(task2Pill).toHaveText("Task 2");

    await contains(task2Pill).click();
    expect(`.o_popover`).toHaveCount(1);
    expect(queryAllTexts`.o_popover .popover-body span`).toEqual([
        "Task 2",
        startDateLocalString,
        stopDateLocalString,
    ]);

    await contains(`.o_popover .popover-header i.fa.fa-close`).click();
    expect(`.o_popover`).toHaveCount(0);
});

test("ordered gantt view", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" progress="progress"/>`,
        groupBy: ["stage_id"],
    });
    const { viewTitle, range, columnHeaders, rows } = getGridContent();
    expect(viewTitle).toBe("Gantt View");
    expect(range).toBe("12/01/2018 -> 02/28/2019");
    expect(columnHeaders).toHaveLength(10);
    expect(columnHeaders.at(0).title).toBe("16");
    expect(columnHeaders.at(-1).title).toBe("25");
    expect(SELECTORS.noContentHelper).toHaveCount(0);
    expect(rows).toEqual([
        {
            title: "todo",
        },
        {
            title: "in_progress",
            pills: [
                { level: 0, colSpan: "Out of bounds (1)  -> Out of bounds (63) ", title: "Task 1" },
                {
                    level: 1,
                    colSpan: "20 (1/2) Dec 2018 -> 20 Dec 2018",
                    title: "Task 7",
                },
            ],
        },
        {
            title: "done",
            pills: [
                {
                    level: 0,
                    colSpan: "17 (1/2) Dec 2018 -> 22 (1/2) Dec 2018",
                    title: "Task 2",
                },
            ],
        },
        {
            title: "cancel",
            pills: [
                {
                    level: 0,
                    colSpan: "20 Dec 2018 -> 20 (1/2) Dec 2018",
                    title: "Task 4",
                },
            ],
        },
    ]);
});

test("empty single-level grouped gantt rendering", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
        groupBy: ["project_id"],
        domain: Domain.FALSE.toList(),
    });
    const { viewTitle, range, columnHeaders, rows } = getGridContent();
    expect(viewTitle).toBe("Gantt View");
    expect(range).toBe("12/01/2018 -> 02/28/2019");
    expect(columnHeaders).toHaveLength(10);
    expect(columnHeaders.at(0).title).toBe("16");
    expect(columnHeaders.at(-1).title).toBe("25");
    expect(rows).toEqual([{ title: "" }]);
    expect(SELECTORS.noContentHelper).toHaveCount(0);
});

test("single-level grouped gantt rendering", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt string="Tasks" date_start="start" date_stop="stop"/>`,
        groupBy: ["project_id"],
    });
    expect(getActiveScale()).toBe(2);
    expect(SELECTORS.expandCollapseButtons).not.toHaveCount();

    const { range, viewTitle, columnHeaders, rows } = getGridContent();
    expect(range).toBe("12/01/2018 -> 02/28/2019");
    expect(viewTitle).toBe("Tasks");
    expect(columnHeaders).toHaveLength(10);
    expect(columnHeaders.at(0).title).toBe("16");
    expect(columnHeaders.at(-1).title).toBe("25");
    expect(rows).toEqual([
        {
            title: "Project 1",
            pills: [
                {
                    title: "Task 1",
                    colSpan: "Out of bounds (1)  -> Out of bounds (63) ",
                    level: 0,
                },
                {
                    title: "Task 2",
                    colSpan: "17 (1/2) Dec 2018 -> 22 (1/2) Dec 2018",
                    level: 1,
                },
                {
                    title: "Task 4",
                    colSpan: "20 Dec 2018 -> 20 (1/2) Dec 2018",
                    level: 2,
                },
            ],
        },
        {
            title: "Project 2",
            pills: [
                {
                    title: "Task 7",
                    colSpan: "20 (1/2) Dec 2018 -> 20 Dec 2018",
                    level: 0,
                },
            ],
        },
    ]);
});

test("Controls: rendering is mobile friendly", async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" />`,
    });

    // check toolbar's dropdown
    await contains("button.dropdown-toggle").click();
    expect(queryAllTexts`.o-dropdown-item`).toEqual(["Activate sparse mode"]);

    // check that pickers open in dialog
    await contains(SELECTORS.rangeMenuToggler).click();
    expect(".modal").toHaveCount(0);
    await contains(SELECTORS.startDatePicker).click();
    expect(".modal").toHaveCount(1);
    expect(".modal-title").toHaveText("Gantt start date");
    expect(".modal-body .o_datetime_picker").toHaveCount(1);
    await contains(".modal-header .btn").click();
    expect(".modal").toHaveCount(0);
    await contains(SELECTORS.stopDatePicker).click();
    expect(".modal").toHaveCount(1);
    expect(".modal-title").toHaveText("Gantt stop date");
    expect(".modal-body .o_datetime_picker").toHaveCount(1);
    await contains(".modal-header .btn").click();
    expect(".modal").toHaveCount(0);
});

test("Progressbar: check the progressbar percentage visibility.", async () => {
    onRpc("get_gantt_data", ({ kwargs, method, parent }) => {
        expect.step(method);
        const result = parent();
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
    expect(SELECTORS.progressBarForeground).toHaveCount(2);
    expect(queryAllTexts(SELECTORS.progressBarForeground)).toEqual(["50h / 100h", "25h / 200h"]);

    // Check the style of one of the progress bars
    expect(rowHeader1.children).toHaveLength(2);
    const rowTitle1 = rowHeader1.children[0];
    expect(rowTitle1.matches(SELECTORS.rowTitle)).toBe(true);
    expect(rowTitle1.nextElementSibling).toBe(progressBar1);

    expect(rowHeader1).toHaveStyle({ gridTemplateRows: "36px 35px" });
    expect(rowTitle1).toHaveStyle({ height: "36px" });
    expect(progressBar1).toHaveStyle({ height: "35px" });
});

test("Progressbar: grouped row", async () => {
    onRpc("get_gantt_data", ({ kwargs, method, parent }) => {
        expect.step(method);
        const result = parent();
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
    expect(SELECTORS.progressBarForeground).toHaveCount(4);
    expect(queryAllTexts(SELECTORS.progressBarForeground)).toEqual([
        "50h / 100h",
        "50h / 100h",
        "25h / 200h",
        "25h / 200h",
    ]);

    // Check the style of one of the progress bars
    expect(rowHeader1.children).toHaveLength(2);
    const rowTitle1 = rowHeader1.children[0];
    expect(rowTitle1.matches(SELECTORS.rowTitle)).toBe(true);
    expect(rowTitle1.nextElementSibling).toBe(progressBar1);

    expect(rowHeader1).toHaveStyle({ gridTemplateRows: "24px 35px" });
    expect(rowTitle1).toHaveStyle({ height: "24px" });
    expect(progressBar1).toHaveStyle({ height: "35px" });
});

test("horizontal scroll applies to the content [SMALL SCREEN]", async () => {
    Tasks._views.gantt = `<gantt date_start="start" date_stop="stop"><field name="user_id"/></gantt>`;
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [[false, "gantt"]],
    });
    await animationFrame();

    const o_view_controller = queryFirst(".o_view_controller");
    const o_content = queryFirst(".o_content");
    const firstColumnHeader = queryFirst(SELECTORS.columnHeader);
    const initialXHeaderCell = firstColumnHeader.getBoundingClientRect().x;

    expect(o_view_controller).toHaveClass("o_action_delegate_scroll");
    expect(o_view_controller).toHaveStyle({ overflow: "hidden" });
    expect(o_content).toHaveStyle({ overflow: "auto" });
    expect(queryFirst(".o_gantt_today").checkVisibility()).toBe(true);
    expect(o_content.scrollLeft).toBeGreaterThan(0);

    // Horizontal scroll
    const newScrollLeft = o_content.scrollLeft - 50;
    await contains(".o_content").scroll({ left: newScrollLeft });

    expect(o_content).toHaveProperty("scrollLeft", newScrollLeft);
    expect(firstColumnHeader.getBoundingClientRect().x).toBe(initialXHeaderCell + 50);
});
