import { test, expect, mockDate } from "@odoo/hoot";
import { defineParams, patchWithCleanup } from "@web/../tests/web_test_helpers";
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

test("slot keys use Latin digits when the UI shows Arabic digits", async () => {
    // 2026-05-19 is a Tuesday, a day with slots for preset "Out"
    mockDate("2026-05-19 10:00:00");
    defineParams({ lang: "ar_001" });
    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(2);
    expect(luxon.Settings.defaultNumberingSystem).toBe("arab");

    expect(Object.keys(preset.availabilities)).toInclude("2026-05-19");
    expect(preset.availabilities["2026-05-19"][0].time).toBe("2026-05-19 12:00:00");
    expect(preset.nextSlot.time).toBe("2026-05-19 12:00:00");
});

test("orders in the POS count toward slot capacity when offline", async () => {
    // 2026-05-19 is a Tuesday, a day with slots for preset "Out"
    mockDate("2026-05-19 10:00:00");
    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(2);
    preset.slots_per_interval = 1;
    store.addNewOrder({
        preset_id: preset,
        preset_time: DateTime.fromSQL("2026-05-19 12:00:00"),
    });
    // Orders without a slot are not counted
    store.addNewOrder({ preset_id: preset, preset_time: false });

    // No server usage, as when the server cannot be reached
    preset.computeAvailabilities();
    const slots = preset.availabilities["2026-05-19"];
    expect(slots.find((s) => s.time === "2026-05-19 12:00:00").isFull).toBe(true);
    expect(slots.find((s) => s.time === "2026-05-19 12:20:00").isFull).toBe(false);
});

test("new floating order preset selection popup is ordered by sequence", async () => {
    const store = await setupPosEnv();
    store.config.available_preset_ids = store.models["pos.preset"]
        .getAll()
        .filter((preset) => [1, 2, 6].includes(preset.id));
    patchWithCleanup(store, {
        shouldSelectPreset: () => true,
    });

    patchWithCleanup(store.dialog, {
        add: (_component, props) => {
            expect(props.list.map((item) => item.label)).toEqual(["Out", "Middle", "In"]);
            props.getPayload(false);
        },
    });

    store.addNewOrder();
});
