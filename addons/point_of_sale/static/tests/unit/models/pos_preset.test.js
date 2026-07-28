import { test, expect, mockDate } from "@odoo/hoot";
import { serializeDateTime } from "@web/core/l10n/dates";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

const { DateTime } = luxon;

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

test("test time off computation", async () => {
    mockDate("1997-12-17"); // Wednesday
    const availableSlots = [
        "1997-12-17 12:00:00",
        "1997-12-17 12:20:00",
        "1997-12-17 12:40:00",
        "1997-12-17 13:00:00",
        "1997-12-17 13:20:00",
        "1997-12-17 13:40:00",
        "1997-12-17 14:00:00",
        "1997-12-17 14:20:00",
        "1997-12-17 14:40:00",
        "1997-12-17 15:00:00",
        "1997-12-17 18:00:00",
        "1997-12-17 18:20:00",
        "1997-12-17 18:40:00",
        "1997-12-17 19:00:00",
        "1997-12-17 19:20:00",
        "1997-12-17 19:40:00",
        "1997-12-17 20:00:00",
        "1997-12-17 20:20:00",
        "1997-12-17 20:40:00",
        "1997-12-17 21:00:00",
        "1997-12-17 21:20:00",
        "1997-12-17 21:40:00",
        "1997-12-17 22:00:00",
    ];

    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(2);
    const availabilities = preset.computeAvailabilities();
    const wednesdaySlots = availabilities["1997-12-17"];
    expect(Object.keys(wednesdaySlots)).toEqual(availableSlots);

    const fakeTimeOff = [
        {
            date_from: serializeDateTime(DateTime.fromSQL("1997-12-17 12:40:00")),
            date_to: serializeDateTime(DateTime.fromSQL("1997-12-17 14:00:00")),
        },
    ];
    const availabilitiesWithOff = preset.computeAvailabilities({}, fakeTimeOff);
    const wednesdaySlotsWithOff = availabilitiesWithOff["1997-12-17"];
    expect(wednesdaySlotsWithOff["1997-12-17 12:40:00"].isFull).toBe(true);
    expect(wednesdaySlotsWithOff["1997-12-17 13:00:00"].isFull).toBe(true);
    expect(wednesdaySlotsWithOff["1997-12-17 13:20:00"].isFull).toBe(true);
    expect(wednesdaySlotsWithOff["1997-12-17 13:40:00"].isFull).toBe(true);
    expect(wednesdaySlotsWithOff["1997-12-17 14:00:00"].isFull).toBe(false);

    fakeTimeOff[0].date_from = serializeDateTime(DateTime.fromSQL("1997-12-17 12:41:00"));
    const availabilitiesWithOff2 = preset.computeAvailabilities({}, fakeTimeOff);
    const wednesdaySlotsWithOff2 = availabilitiesWithOff2["1997-12-17"];
    expect(wednesdaySlotsWithOff2["1997-12-17 12:40:00"].isFull).toBe(true);
    expect(wednesdaySlotsWithOff2["1997-12-17 13:00:00"].isFull).toBe(true);
    expect(wednesdaySlotsWithOff2["1997-12-17 13:20:00"].isFull).toBe(true);
    expect(wednesdaySlotsWithOff2["1997-12-17 13:40:00"].isFull).toBe(true);
    expect(wednesdaySlotsWithOff2["1997-12-17 14:00:00"].isFull).toBe(false);
});
