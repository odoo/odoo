import { test, expect } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("generateSlots", async () => {
    const store = await setupPosEnv();
    const presetIn = store.models["pos.preset"].get(1);
    // expect all presetIn.availabilities to be empty arrays
    for (const key in presetIn.availabilities) {
        expect(Array.isArray(presetIn.availabilities[key])).toBe(true);
        expect(presetIn.availabilities[key].length).toBe(0);
    }
    // expect days of week of presetOut.availabilities to contains slots
    const presetOut = store.models["pos.preset"].get(2);
    let daysWithSlot = 0;
    for (const key in presetOut.availabilities) {
        if (Object.keys(presetOut.availabilities[key]).length > 0) {
            daysWithSlot++;
            // each day should contains 23 slots of 20 minutes (12:00 to 15:00, and 18:00 to 22:00)
            expect(Object.keys(presetOut.availabilities[key]).length).toBe(23);
        }
    }
    // expect at least 5 days with slots (Monday to Friday)
    expect(daysWithSlot).toBe(5);
});

test("generateSlots with a two weeks calendar", async () => {
    // Thursday of a "first" week: the next 7 days span Thu-Sun of the first
    // week and Mon-Wed of the second week.
    mockDate("2026-10-01 08:00:00");
    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(2);
    const attendanceModel = store.models["resource.calendar.attendance"];
    const section = { display_type: "line_section", dayofweek: "0", hour_from: 0, hour_to: 0 };
    const opening = { dayofweek: "1", hour_from: 18, hour_to: 22, day_period: "afternoon" };
    preset.attendance_ids = [
        attendanceModel.create({ ...section, week_type: "0" }),
        attendanceModel.create({ ...section, week_type: "1" }),
        // Only opened on Tuesday and Friday of the second week
        attendanceModel.create({ ...opening, week_type: "1" }),
        attendanceModel.create({ ...opening, week_type: "1", dayofweek: "4" }),
    ];
    preset.generateSlots();

    const daysWithSlot = Object.entries(preset.availabilities)
        .filter(([, slots]) => Object.keys(slots).length)
        .map(([date]) => date);
    expect(daysWithSlot).toEqual(["2026-10-06"]);
    expect(Object.keys(preset.availabilities["2026-10-06"]).length).toBe(13);
});
