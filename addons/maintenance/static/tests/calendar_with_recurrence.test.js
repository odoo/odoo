import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    preloadFullCalendar,
} from "@web/../tests/web_test_helpers";

class MaintenanceRequest extends models.Model {
    _name = "maintenance.request";

    name = fields.Char();
    schedule_date = fields.Datetime();
    schedule_end = fields.Datetime();
    duration = fields.Float();
    recurring_maintenance = fields.Boolean();
    repeat_interval = fields.Integer();
    repeat_unit = fields.Selection({
        selection: [
            ["day", "Days"],
            ["week", "Weeks"],
            ["month", "Months"],
        ],
    });
    repeat_type = fields.Selection({
        selection: [
            ["forever", "Forever"],
            ["until", "Until"],
        ],
    });
    repeat_until = fields.Date();
    date_recurrence_origin = fields.Datetime();
    done = fields.Boolean();
    archive = fields.Boolean();

    has_access() {
        return true;
    }

    _records = [
        {
            id: 1,
            name: "daily check",
            schedule_date: "2026-09-14 16:00:00",
            schedule_end: "2026-09-14 17:00:00",
            duration: 1,
            recurring_maintenance: true,
            repeat_interval: 1,
            repeat_unit: "day",
            repeat_type: "until",
            repeat_until: "2026-09-17",
        },
        {
            id: 2,
            name: "last year's repair",
            schedule_date: "2025-09-10 16:00:00",
            schedule_end: "2025-09-10 17:00:00",
            duration: 1,
        },
    ];
}

defineModels([MaintenanceRequest]);
preloadFullCalendar();

const arch = `
    <calendar js_class="calendar_with_recurrence" date_start="schedule_date" date_stop="schedule_end" mode="week">
        <field name="recurring_maintenance" invisible="1"/>
        <field name="repeat_interval" invisible="1"/>
        <field name="repeat_unit" invisible="1"/>
        <field name="repeat_type" invisible="1"/>
        <field name="repeat_until" invisible="1"/>
        <field name="date_recurrence_origin" invisible="1"/>
        <field name="done" invisible="1"/>
        <field name="archive" invisible="1"/>
        <field name="duration" invisible="1"/>
    </calendar>
`;

test.tags("desktop");
test("an until recurrence still shows its occurrence on the end date west of UTC", async () => {
    mockDate("2026-09-14T08:00:00", -6);
    await mountView({ resModel: "maintenance.request", type: "calendar", arch });
    expect(queryAllTexts(".fc-event .o_event_title")).toEqual([
        "daily check",
        "daily check (+1)",
        "daily check (+2)",
        "daily check (+3)",
    ]);
});

test.tags("desktop");
test("a monthly series from the 31st shows its occurrence on the month end", async () => {
    MaintenanceRequest._records = [
        {
            id: 3,
            name: "month end",
            schedule_date: "2026-01-31 16:00:00",
            schedule_end: "2026-01-31 17:00:00",
            duration: 1,
            recurring_maintenance: true,
            repeat_interval: 1,
            repeat_unit: "month",
            repeat_type: "forever",
        },
        {
            id: 4,
            name: "rescheduled",
            schedule_date: "2026-03-03 16:00:00",
            schedule_end: "2026-03-03 17:00:00",
            date_recurrence_origin: "2026-01-31 16:00:00",
            duration: 1,
            recurring_maintenance: true,
            repeat_interval: 1,
            repeat_unit: "month",
            repeat_type: "forever",
        },
    ];
    mockDate("2026-03-15T08:00:00", -6);
    await mountView({
        resModel: "maintenance.request",
        type: "calendar",
        arch: arch.replace('mode="week"', 'mode="month"'),
    });
    expect(
        queryAllTexts(".fc-daygrid-day[data-date='2026-03-31'] .o_event_title"),
    ).toEqual(["month end (+2)", "rescheduled (+1)"]);
    expect(".fc-daygrid-day[data-date='2026-03-28'] .fc-event").toHaveCount(0);
});

test.tags("desktop");
test("a finished request that cannot repeat into the range is not fetched", async () => {
    mockDate("2026-09-14T08:00:00", -6);
    onRpc("maintenance.request", "search_read", async ({ parent }) => {
        const records = await parent();
        expect.step(records.map((record) => record.id));
        return records;
    });
    await mountView({ resModel: "maintenance.request", type: "calendar", arch });
    expect.verifySteps([[1]]);
});
