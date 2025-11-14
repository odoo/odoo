import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { mockDate } from "@odoo/hoot-mock";

definePosModels();

describe("generateSlots", () => {
    test("presetIn", async () => {
        mockDate("2025-09-24T10:00:00", +0);
        const store = await setupPosEnv();

        // expect all presetIn.availabilities to be empty arrays
        const presetIn = store.models["pos.preset"].get(1);
        for (const key in presetIn.availabilities) {
            expect(Array.isArray(presetIn.availabilities[key])).toBe(true);
            expect(presetIn.availabilities[key].length).toBe(0);
        }
    });

    test("presetOut 10h00", async () => {
        mockDate("2025-09-24T10:00:00", +0);
        const store = await setupPosEnv();

        // expect days of week of presetOut.availabilities to contains slots
        const presetOut = store.models["pos.preset"].get(2);
        for (const key in presetOut.availabilities) {
            const slotsClount = Object.keys(presetOut.availabilities[key]).length;

            // Sunday - Monday
            if (key === "2025-09-28" || key === "2025-09-29") {
                expect(slotsClount).toBe(0);
            }
            // Other days should contains 23 slots of 20 minutes (12:00 to 15:00, and 18:00 to 22:00)
            else {
                expect(slotsClount).toBe(23);
            }
        }
    });

    test("presetOut 14h15", async () => {
        mockDate("2025-09-24T14:15:00", +0);
        const store = await setupPosEnv();

        // expect days of week of presetOut.availabilities to contains slots
        const presetOut = store.models["pos.preset"].get(2);
        for (const key in presetOut.availabilities) {
            const slotsClount = Object.keys(presetOut.availabilities[key]).length;

            // Sunday - Monday
            if (key === "2025-09-28" || key === "2025-09-29") {
                expect(slotsClount).toBe(0);
            }
            // Wednesday (today) should contains slots from 14:20 to 15:00, and 18:00 to 22:00 (16 slots)
            else if (key === "2025-09-24") {
                expect(slotsClount).toBe(16);
            }
            // Other days should contains 23 slots of 20 minutes (12:00 to 15:00, and 18:00 to 22:00)
            else {
                expect(slotsClount).toBe(23);
            }
        }
    });

    test("presetOut 21h15", async () => {
        mockDate("2025-09-24T21:15:00", +0);
        const store = await setupPosEnv();

        // expect days of week of presetOut.availabilities to contains slots
        const presetOut = store.models["pos.preset"].get(2);
        for (const key in presetOut.availabilities) {
            const slotsClount = Object.keys(presetOut.availabilities[key]).length;

            // Sunday - Monday
            if (key === "2025-09-28" || key === "2025-09-29") {
                expect(slotsClount).toBe(0);
            }
            // Wednesday (today) should contains slots from 21:20 22:00 (3 slots)
            else if (key === "2025-09-24") {
                expect(slotsClount).toBe(3);
            }
            // Other days should contains 23 slots of 20 minutes (12:00 to 15:00, and 18:00 to 22:00)
            else {
                expect(slotsClount).toBe(23);
            }
        }
    });

    test("presetOut 23h00", async () => {
        mockDate("2025-09-24T23:00:00", +0);
        const store = await setupPosEnv();

        // expect days of week of presetOut.availabilities to contains slots
        const presetOut = store.models["pos.preset"].get(2);
        for (const key in presetOut.availabilities) {
            const slotsClount = Object.keys(presetOut.availabilities[key]).length;

            // Wednesday (today) - Sunday - Monday
            if (key === "2025-09-24" || key === "2025-09-28" || key === "2025-09-29") {
                expect(slotsClount).toBe(0);
            }
            // Other days should contains 23 slots of 20 minutes (12:00 to 15:00, and 18:00 to 22:00)
            else {
                expect(slotsClount).toBe(23);
            }
        }
    });
});
