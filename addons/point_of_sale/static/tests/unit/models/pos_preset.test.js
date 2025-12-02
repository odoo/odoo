import { test, expect } from "@odoo/hoot";
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
