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

class MaintenancePlan extends models.Model {
    _name = "maintenance.plan";

    name = fields.Char();
    active = fields.Boolean({ default: true });
    repeat_type = fields.Selection({
        selection: [
            ["forever", "Forever"],
            ["until", "Until"],
        ],
    });
    repeat_until = fields.Date();

    _records = [
        {
            id: 1,
            name: "daily",
            active: true,
            repeat_type: "until",
            repeat_until: "2026-09-17",
        },
        { id: 2, name: "stopped", active: false, repeat_type: "forever" },
    ];
}

class MaintenanceRequest extends models.Model {
    _name = "maintenance.request";

    name = fields.Char();
    schedule_date = fields.Datetime();
    schedule_end = fields.Datetime();
    duration = fields.Float();
    plan_id = fields.Many2one({ relation: "maintenance.plan" });
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
            plan_id: 1,
        },
        {
            id: 2,
            name: "last year's repair",
            schedule_date: "2025-09-10 16:00:00",
            schedule_end: "2025-09-10 17:00:00",
            duration: 1,
        },
        {
            id: 3,
            name: "stopped plan",
            schedule_date: "2025-09-11 16:00:00",
            schedule_end: "2025-09-11 17:00:00",
            duration: 1,
            plan_id: 2,
        },
    ];
}

defineModels([MaintenancePlan, MaintenanceRequest]);
preloadFullCalendar();

const arch = `
    <calendar js_class="calendar_with_recurrence" date_start="schedule_date" date_stop="schedule_end" mode="week">
        <field name="plan_id" invisible="1"/>
        <field name="done" invisible="1"/>
        <field name="archive" invisible="1"/>
        <field name="duration" invisible="1"/>
    </calendar>
`;

test.tags("desktop");
test("a plan's request shows the occurrences the server projects for it", async () => {
    mockDate("2026-09-14T08:00:00", -6);
    onRpc("maintenance.request", "get_plan_occurrences", ({ args }) => {
        expect.step(args[0]);
        return {
            1: ["2026-09-15 16:00:00", "2026-09-16 16:00:00", "2026-09-17 16:00:00"],
        };
    });
    await mountView({ resModel: "maintenance.request", type: "calendar", arch });
    expect.verifySteps([[1]]);
    expect(queryAllTexts(".fc-event .o_event_title")).toEqual([
        "daily check",
        "daily check (+1)",
        "daily check (+2)",
        "daily check (+3)",
    ]);
});

test.tags("desktop");
test("a request that cannot repeat into the range is not fetched", async () => {
    mockDate("2026-09-14T08:00:00", -6);
    onRpc("maintenance.request", "get_plan_occurrences", () => ({}));
    onRpc("maintenance.request", "search_read", async ({ parent }) => {
        const records = await parent();
        expect.step(records.map((record) => record.id));
        return records;
    });
    await mountView({ resModel: "maintenance.request", type: "calendar", arch });
    expect.verifySteps([[1]]);
});
