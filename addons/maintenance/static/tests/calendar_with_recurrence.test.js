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

class MaintenanceOrder extends models.Model {
    _name = "maintenance.order";

    name = fields.Char();
    date_scheduled_start = fields.Datetime();
    date_scheduled_end = fields.Datetime();
    duration = fields.Float();
    plan_id = fields.Many2one({ relation: "maintenance.plan" });
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["confirmed", "Confirmed"],
            ["in_progress", "In Progress"],
            ["done", "Done"],
            ["cancel", "Cancelled"],
        ],
        default: "confirmed",
    });

    has_access() {
        return true;
    }

    _records = [
        {
            id: 1,
            name: "daily check",
            date_scheduled_start: "2026-09-14 16:00:00",
            date_scheduled_end: "2026-09-14 17:00:00",
            duration: 1,
            plan_id: 1,
        },
        {
            id: 2,
            name: "last year's repair",
            date_scheduled_start: "2025-09-10 16:00:00",
            date_scheduled_end: "2025-09-10 17:00:00",
            duration: 1,
        },
        {
            id: 4,
            name: "closed occurrence of an active plan",
            date_scheduled_start: "2025-09-12 16:00:00",
            date_scheduled_end: "2025-09-12 17:00:00",
            duration: 1,
            plan_id: 1,
            state: "done",
        },
        {
            id: 3,
            name: "stopped plan",
            date_scheduled_start: "2025-09-11 16:00:00",
            date_scheduled_end: "2025-09-11 17:00:00",
            duration: 1,
            plan_id: 2,
        },
    ];
}

defineModels([MaintenancePlan, MaintenanceOrder]);
preloadFullCalendar();

const arch = `
    <calendar js_class="calendar_with_recurrence" date_start="date_scheduled_start" date_stop="date_scheduled_end" mode="week">
        <field name="plan_id" invisible="1"/>
        <field name="state" invisible="1"/>
        <field name="duration" invisible="1"/>
    </calendar>
`;

test.tags("desktop");
test("a plan's order shows the occurrences the server projects for it", async () => {
    mockDate("2026-09-14T08:00:00", -6);
    onRpc("maintenance.order", "get_plan_occurrences", ({ args }) => {
        expect.step(args[0]);
        return {
            1: ["2026-09-15 16:00:00", "2026-09-16 16:00:00", "2026-09-17 16:00:00"],
        };
    });
    await mountView({ resModel: "maintenance.order", type: "calendar", arch });
    expect.verifySteps([[1]]);
    expect(queryAllTexts(".fc-event .o_event_title")).toEqual([
        "daily check",
        "daily check (+1)",
        "daily check (+2)",
        "daily check (+3)",
    ]);
});

test.tags("desktop");
test("an order that cannot repeat into the range is not fetched", async () => {
    mockDate("2026-09-14T08:00:00", -6);
    onRpc("maintenance.order", "get_plan_occurrences", () => ({}));
    onRpc("maintenance.order", "search_read", async ({ parent }) => {
        const records = await parent();
        expect.step(records.map((record) => record.id));
        return records;
    });
    await mountView({ resModel: "maintenance.order", type: "calendar", arch });
    expect.verifySteps([[1]]);
});
