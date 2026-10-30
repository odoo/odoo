import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { serializeDateTime } from "@web/core/l10n/dates";

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

test("computeAvailabilities with leaves", async () => {
    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(2);
    const [date] = preset.getAvailableDates();
    const [before, first, second, after] = Object.values(preset.availabilities[date]);
    preset.computeAvailabilities({}, [
        [
            serializeDateTime(first.datetime),
            serializeDateTime(second.datetime.plus({ minutes: 1 })),
        ],
    ]);
    const slotTimes = Object.values(preset.availabilities[date]).map((s) => s.datetime.ts);
    expect(slotTimes).toInclude(before.datetime.ts);
    expect(slotTimes).not.toInclude(first.datetime.ts);
    expect(slotTimes).not.toInclude(second.datetime.ts);
    expect(slotTimes).toInclude(after.datetime.ts);

    preset.computeAvailabilities();
    expect(Object.keys(preset.availabilities[date])).toHaveLength(slotTimes.length);

    preset.computeAvailabilities({}, [
        [
            serializeDateTime(before.datetime.minus({ days: 1 })),
            serializeDateTime(before.datetime.plus({ days: 8 })),
        ],
    ]);
    expect(preset.getAvailableDates()).toHaveLength(0);
});

test("full slots remain available to the orders booked in them", async () => {
    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(2);
    preset.slots_per_interval = 1;
    const [date] = preset.getAvailableDates();
    const [ownSlot, ...otherSlots] = Object.keys(preset.availabilities[date]);
    preset.computeAvailabilities({
        [ownSlot]: [1],
        ...Object.fromEntries(otherSlots.map((slot) => [slot, [2]])),
    });

    const order = { id: 1 };
    const slots = preset.availabilities[date];
    expect(preset.getAvailableDates()).not.toInclude(date);
    expect(preset.getAvailableDates(order)).toInclude(date);
    expect(preset.isSlotAvailable(slots[ownSlot], order)).toBe(true);
    expect(preset.isSlotAvailable(slots[otherSlots[0]], order)).toBe(false);
});
