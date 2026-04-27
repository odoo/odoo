import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { defineModels, fields, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    SELECTORS,
    getCell,
    getCellColorProperties,
    hoverGridCell,
    mountGanttView,
} from "@web_gantt/../tests/web_gantt_test_helpers";

describe.current.tags("desktop");

class Workorder extends models.Model {
    name = fields.Char();
    planned_start = fields.Datetime();
    planned_stop = fields.Datetime();
    workcenter_id = fields.Many2one({ string: "Work Center", relation: "workcenter" });

    _records = [
        {
            id: 1,
            name: "Blop",
            planned_start: "2023-02-24 08:00:00",
            planned_stop: "2023-03-20 08:00:00",
            workcenter_id: 1,
        },
        {
            id: 2,
            name: "Yop",
            planned_start: "2023-02-22 08:00:00",
            planned_stop: "2023-03-27 08:00:00",
            workcenter_id: 2,
        },
    ];

    _views = {
        form: `
            <form>
                <field name="name"/>
                <field name="start_datetime"/>
                <field name="date_deadline"/>
            </form>
        `,
    };
}

class Workcenter extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "Assembly Line 1" },
        { id: 2, name: "Assembly Line 2" },
    ];
}

defineMailModels();
defineModels([Workorder, Workcenter]);

test("progress bar has the correct unit", async () => {
    expect.assertions(11);

    mockDate("2023-03-05 07:00:00");
    onRpc("get_gantt_data", ({ kwargs, parent }) => {
        const result = parent();
        expect(kwargs.progress_bar_fields).toEqual(["workcenter_id"]);
        result.progress_bars.workcenter_id = {
            1: { value: 465, max_value: 744 },
            2: { value: 651, max_value: 744 },
        };
        return result;
    });

    await mountGanttView({
        arch: `
            <gantt js_class="mrp_workorder_gantt"
                date_start="planned_start"
                date_stop="planned_stop"
                progress_bar="workcenter_id"
            />
        `,
        resModel: "workorder",
        groupBy: ["workcenter_id"],
    });
    expect(SELECTORS.progressBar).toHaveCount(2);
    expect(SELECTORS.progressBarBackground).toHaveCount(2);
    expect(queryAll(SELECTORS.progressBarBackground).map((el) => el.style.width)).toEqual([
        "62.5%",
        "87.5%",
    ]);

    expect(SELECTORS.progressBarForeground).toHaveCount(0);

    await hoverGridCell("01 March 2023", "Assembly Line 1");
    expect(SELECTORS.progressBarForeground).toHaveCount(1);
    expect(SELECTORS.progressBarForeground).toHaveText("465h / 744h");
    expect(`${SELECTORS.progressBar} > span > .o_gantt_group_hours_ratio`).toHaveText("(62.5%)");

    await hoverGridCell("01 March 2023", "Assembly Line 2");
    expect(SELECTORS.progressBarForeground).toHaveCount(1);
    expect(SELECTORS.progressBarForeground).toHaveText("651h / 744h");
    expect(`${SELECTORS.progressBar} > span > .o_gantt_group_hours_ratio`).toHaveText("(87.5%)");
});

test("unavailabilities fetched for workcenter_id (in groupBy)", async () => {
    mockDate("2023-03-05 07:00:00");
    onRpc("get_gantt_data", ({ parent, kwargs }) => {
        const result = parent();
        expect.step("get_gantt_data");
        expect(kwargs.unavailability_fields).toEqual(["workcenter_id"]);
        result.unavailabilities.workcenter_id = {
            1: [{ start: "2023-03-05 07:00:00", stop: "2023-03-06 07:00:00" }],
        };
        return result;
    });
    await mountGanttView({
        resModel: "workorder",
        arch: `
            <gantt js_class="mrp_workorder_gantt" date_start="planned_start" date_stop="planned_stop" display_unavailability="1">
                <field name="workcenter_id" />
            </gantt>
        `,
        groupBy: ["workcenter_id"],
    });
    expect.verifySteps(["get_gantt_data"]);
    expect(getCell("05 March 2023")).toHaveClass("o_gantt_today");
    expect(getCellColorProperties("05 March 2023")).toEqual([
        "--Gantt__DayOffToday-background-color",
        "--Gantt__DayOff-background-color",
    ]);
    expect(getCell("05 March 2023", "Assembly line 2")).toHaveClass("o_gantt_today");
    expect(getCellColorProperties("05 March 2023", "Assembly line 2")).toEqual([]);
});

test("unavailabilities fetched for workcenter_id  (not in groupBy)", async () => {
    mockDate("2023-03-05 07:00:00");
    Workorder._fields.other_workcenter_id = fields.Many2one({
        string: "Other Work Center",
        relation: "workcenter",
    });
    Workorder._records[0].other_workcenter_id = 1;
    onRpc("get_gantt_data", ({ parent, kwargs }) => {
        const result = parent();
        expect.step("get_gantt_data");
        expect(kwargs.unavailability_fields).toEqual([]);
        result.unavailabilities.workcenter_id = {
            1: [{ start: "2023-03-05 07:00:00", stop: "2023-03-06 07:00:00" }],
        };
        return result;
    });
    await mountGanttView({
        resModel: "workorder",
        arch: `
            <gantt js_class="mrp_workorder_gantt" date_start="planned_start" date_stop="planned_stop">
                <field name="workcenter_id" />
            </gantt>
        `,
        groupBy: ["other_workcenter_id"],
    });
    expect.verifySteps(["get_gantt_data"]);
    expect(getCell("05 March 2023")).toHaveClass("o_gantt_today");
    expect(getCellColorProperties("05 March 2023")).toEqual([]);
});
