import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockDate, advanceTime, runAllTimers } from "@odoo/hoot-mock";
import {
    defineModels,
    defineParams,
    fields,
    models,
    onRpc,
    contains,
} from "@web/../tests/web_test_helpers";
import {
    getCell,
    getGridContent,
    mountGanttView,
    SELECTORS,
} from "@web_gantt/../tests/web_gantt_test_helpers";

describe.current.tags("desktop");

class Attendances extends models.Model {
    name = fields.Char();
    check_in = fields.Datetime({ string: "Start Date" });
    check_out = fields.Datetime({ string: "Stop Date" });
    user_id = fields.Many2one({ string: "Attendance Of", relation: "users" });

    _records = [
        {
            id: 1,
            check_in: "2018-12-10 09:00:00",
            check_out: "2018-12-10 12:00:00",
            name: "Attendance 1",
            user_id: 1,
        },
        {
            id: 2,
            check_in: "2018-12-10 13:00:00",
            check_out: false,
            name: "Attendance 2",
            user_id: 1,
        },
        {
            id: 3,
            check_in: "2018-12-10 08:00:00",
            check_out: "2018-12-10 16:00:00",
            name: "Attendance 3",
            user_id: 2,
        },
    ];
}

class Users extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "User 1" },
        { id: 2, name: "User 2" },
    ];
}

defineMailModels();
defineModels([Attendances, Users]);

beforeEach(() => {
    defineParams({
        lang_parameters: {
            time_format: "%I:%M:%S",
        },
    });
});

test("Open Ended record today", async () => {
    mockDate("2018-12-10 16:00:00");
    await mountGanttView({
        resModel: "attendances",
        arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
        context: {
            default_start_date: "2018-12-10",
            default_stop_date: "2018-12-10",
        },
    });
    const { range, rows } = getGridContent();
    expect(range).toBe("12/10/2018 -> 12/10/2018");
    expect(rows).toEqual([
        {
            pills: [
                {
                    colSpan: "10am 10 December 2018 -> 12pm 10 December 2018",
                    level: 0,
                    title: "Attendance 1",
                },
                {
                    colSpan: "2pm 10 December 2018 -> 5pm 10 December 2018",
                    level: 0,
                    title: "Attendance 2",
                },
            ],
            title: "User 1",
        },
        {
            pills: [
                {
                    colSpan: "9am 10 December 2018 -> 4pm 10 December 2018",
                    level: 0,
                    title: "Attendance 3",
                },
            ],
            title: "User 2",
        },
    ]);
});

test("Future Open Ended record not displayed", async () => {
    mockDate("2018-12-10 12:00:00");
    await mountGanttView({
        resModel: "attendances",
        arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
        context: {
            default_start_date: "2018-12-10",
            default_stop_date: "2018-12-10",
        },
    });
    const { range, rows } = getGridContent();
    expect(range).toBe("12/10/2018 -> 12/10/2018");
    expect(rows).toEqual([
        {
            pills: [
                {
                    colSpan: "10am 10 December 2018 -> 12pm 10 December 2018",
                    level: 0,
                    title: "Attendance 1",
                },
            ],
            title: "User 1",
        },
        {
            pills: [
                {
                    colSpan: "9am 10 December 2018 -> 4pm 10 December 2018",
                    level: 0,
                    title: "Attendance 3",
                },
            ],
            title: "User 2",
        },
    ]);
});

test("Open Ended record spanning multiple days", async () => {
    mockDate("2018-12-12 14:00:00");
    await mountGanttView({
        resModel: "attendances",
        arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
        context: {
            default_start_date: "2018-12-12",
            default_stop_date: "2018-12-12",
        },
    });
    let gridContent = getGridContent();
    expect(gridContent.range).toBe("12/12/2018 -> 12/12/2018");
    expect(gridContent.rows).toEqual([
        {
            pills: [
                {
                    colSpan: "12am 12 December 2018 -> 3pm 12 December 2018",
                    level: 0,
                    title: "Attendance 2",
                },
            ],
            title: "User 1",
        },
    ]);
    await click(queryOne(SELECTORS.previousButton));
    await advanceTime(500);
    await animationFrame();
    gridContent = getGridContent();
    expect(gridContent.range).toBe("12/11/2018 -> 12/11/2018");
    expect(gridContent.rows).toEqual([
        {
            pills: [
                {
                    colSpan: "12am 11 December 2018 -> 11pm 11 December 2018",
                    level: 0,
                    title: "Attendance 2",
                },
            ],
            title: "User 1",
        },
    ]);
    await click(queryOne(SELECTORS.previousButton));
    await advanceTime(500);
    await animationFrame();
    gridContent = getGridContent();
    expect(gridContent.range).toBe("12/10/2018 -> 12/10/2018");
    expect(gridContent.rows).toEqual([
        {
            pills: [
                {
                    colSpan: "10am 10 December 2018 -> 12pm 10 December 2018",
                    level: 0,
                    title: "Attendance 1",
                },
                {
                    colSpan: "2pm 10 December 2018 -> 11pm 10 December 2018",
                    level: 0,
                    title: "Attendance 2",
                },
            ],
            title: "User 1",
        },
        {
            pills: [
                {
                    colSpan: "9am 10 December 2018 -> 4pm 10 December 2018",
                    level: 0,
                    title: "Attendance 3",
                },
            ],
            title: "User 2",
        },
    ]);
});

test("Concurrent open-ended records", async () => {
    mockDate("2018-12-20 15:00:00");
    Attendances._records = [
        {
            id: 4,
            check_in: "2018-12-20 08:00:00",
            check_out: false,
            name: "Attendance 4",
            user_id: 1,
        },
        {
            id: 5,
            check_in: "2018-12-20 09:00:00",
            check_out: false,
            name: "Attendance 5",
            user_id: 1,
        },
    ];

    await mountGanttView({
        resModel: "attendances",
        arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
        context: {
            default_start_date: "2018-12-20",
            default_stop_date: "2018-12-20",
        },
    });
    const { range, rows } = getGridContent();
    expect(range).toBe("12/20/2018 -> 12/20/2018");
    expect(rows).toEqual([
        {
            pills: [
                {
                    colSpan: "9am 20 December 2018 -> 4pm 20 December 2018",
                    level: 0,
                    title: "Attendance 4",
                },
                {
                    colSpan: "10am 20 December 2018 -> 4pm 20 December 2018",
                    level: 1,
                    title: "Attendance 5",
                },
            ],
            title: "User 1",
        },
    ]);
});

test("Open ended record Precision", async () => {
    mockDate("2018-12-20 15:35:00");
    Attendances._records = [
        {
            id: 4,
            check_in: "2018-12-20 08:00:00",
            check_out: false,
            name: "Attendance 4",
            user_id: 1,
        },
    ];

    await mountGanttView({
        resModel: "attendances",
        arch: `<gantt js_class="attendance_gantt" date_start="check_in" precision="{'day': 'hour:quarter'}" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
        context: {
            default_start_date: "2018-12-20",
            default_stop_date: "2018-12-20",
        },
    });
    const { range, rows } = getGridContent();
    expect(range).toBe("12/20/2018 -> 12/20/2018");
    expect(rows).toEqual([
        {
            pills: [
                {
                    colSpan: "9am 20 December 2018 -> 4pm (3/4) 20 December 2018",
                    level: 0,
                    title: "Attendance 4",
                },
            ],
            title: "User 1",
        },
    ]);
});

test("Open ended record updated correctly", async () => {
    mockDate("2018-12-20 14:00:00");
    Attendances._records = [
        {
            id: 4,
            check_in: "2018-12-20 08:00:00",
            check_out: false,
            name: "Attendance 4",
            user_id: 1,
        },
    ];

    await mountGanttView({
        resModel: "attendances",
        arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
        context: {
            default_start_date: "2018-12-20",
            default_stop_date: "2018-12-20",
        },
    });
    let gridContent = getGridContent();
    expect(gridContent.range).toBe("12/20/2018 -> 12/20/2018");
    expect(gridContent.rows).toEqual([
        {
            pills: [
                {
                    colSpan: "9am 20 December 2018 -> 3pm 20 December 2018",
                    level: 0,
                    title: "Attendance 4",
                },
            ],
            title: "User 1",
        },
    ]);
    mockDate("2018-12-20 18:00:00");
    await click(queryOne(SELECTORS.previousButton));
    await advanceTime(500);
    await animationFrame();
    await click(queryOne(SELECTORS.nextButton));
    await advanceTime(500);
    await animationFrame();
    gridContent = getGridContent();
    expect(gridContent.range).toBe("12/20/2018 -> 12/20/2018");
    // TODO fixme: end hour is non deterministic and alternates between 7pm and 8pm.
    const endHour = parseInt(gridContent.rows[0].pills[0].colSpan.match(/->\s*(\d+)/)[1]);
    expect(endHour).toBeWithin(7, 8);
    expect(gridContent.rows).toEqual([
        {
            pills: [
                {
                    colSpan: `9am 20 December 2018 -> ${endHour}pm 20 December 2018`,
                    level: 0,
                    title: "Attendance 4",
                },
            ],
            title: "User 1",
        },
    ]);
});

test("Future Open ended record not shown before it happens and appears after start date.", async () => {
    mockDate("2018-11-02 12:00:00");
    Attendances._records = [
        {
            id: 5,
            check_in: "2018-11-02 09:00:00",
            check_out: "2018-11-02 12:00:00",
            name: "Attendance 5",
            user_id: 1,
        },
        {
            id: 6,
            check_in: "2018-11-02 14:00:00",
            check_out: false,
            name: "Attendance 6",
            user_id: 1,
        },
    ];

    await mountGanttView({
        resModel: "attendances",
        arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
        context: {
            default_start_date: "2018-11-02",
            default_stop_date: "2018-11-02",
        },
    });
    let gridContent = getGridContent();
    expect(gridContent.range).toBe("11/02/2018 -> 11/02/2018");
    expect(gridContent.rows).toEqual([
        {
            pills: [
                {
                    colSpan: "10am 02 November 2018 -> 12pm 02 November 2018",
                    level: 0,
                    title: "Attendance 5",
                },
            ],
            title: "User 1",
        },
    ]);
    mockDate("2018-11-02 17:00:00");
    await click(queryOne(SELECTORS.previousButton));
    await advanceTime(500);
    await animationFrame();
    await click(queryOne(SELECTORS.nextButton));
    await advanceTime(500);
    await animationFrame();
    gridContent = getGridContent();
    expect(gridContent.range).toBe("11/02/2018 -> 11/02/2018");
    expect(gridContent.rows).toEqual([
        {
            pills: [
                {
                    colSpan: "10am 02 November 2018 -> 12pm 02 November 2018",
                    level: 0,
                    title: "Attendance 5",
                },
                {
                    colSpan: "3pm 02 November 2018 -> 6pm 02 November 2018",
                    level: 0,
                    title: "Attendance 6",
                },
            ],
            title: "User 1",
        },
    ]);
});

test("Domain correctly applied when allow_open_ended=1.", async () => {
    mockDate("2018-11-02 19:00:00");
    Attendances._records = [
        {
            id: 7,
            check_in: "2018-11-02 15:00:00",
            check_out: "2018-11-02 19:00:00",
            name: "Attendance 7",
            user_id: 2,
        },
        {
            id: 8,
            check_in: "2018-11-02 14:00:00",
            check_out: false,
            name: "Attendance 8",
            user_id: 1,
        },
        {
            id: 9,
            check_in: "2018-11-02 08:00:00",
            check_out: "2018-11-02 14:00:00",
            name: "Attendance 9",
            user_id: 1,
        },
    ];

    await mountGanttView({
        resModel: "attendances",
        arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
        domain: ["|", ["user_id", "=", 2], ["check_out", "=", false]],
        context: {
            default_start_date: "2018-11-02",
            default_stop_date: "2018-11-02",
        },
    });
    const { rows, range } = getGridContent();
    expect(range).toBe("11/02/2018 -> 11/02/2018");
    expect(rows).toEqual([
        {
            pills: [
                {
                    colSpan: "3pm 02 November 2018 -> 8pm 02 November 2018",
                    level: 0,
                    title: "Attendance 8",
                },
            ],
            title: "User 1",
        },
        {
            pills: [
                {
                    colSpan: "4pm 02 November 2018 -> 7pm 02 November 2018",
                    level: 0,
                    title: "Attendance 7",
                },
            ],
            title: "User 2",
        },
    ]);
});

test("Dragging half column in week scale preserves checkout context", async () => {
    expect.assertions(2);
    mockDate("2025-08-01 14:00:00");
    Attendances._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="check_in"/>
                <field name="check_out"/>
                <field name="user_id"/>
            </form>
        `,
    };
    onRpc("onchange", ({ kwargs }) => {
        expect(kwargs.context.check_out).not.toBeEmpty();
        expect(kwargs.context.default_check_out).not.toBeEmpty();
    });
    await mountGanttView({
        resModel: "attendances",
        arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="week" date_stop="check_out" plan="false"/>`,
        context: {
            default_start_date: "2025-08-01",
            default_stop_date: "2025-08-07",
        },
    });
    const { moveTo, drop } = await contains(getCell("01 W31 2025", "User 1")).drag();
    moveTo(getCell("01 W31 2025", "User 1"));
    await runAllTimers(); // Pointer move is subjected to throttleForAnimation in gantt
    await drop();
    await animationFrame();
});
