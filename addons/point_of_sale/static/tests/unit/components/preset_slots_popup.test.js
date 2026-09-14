import { Deferred, expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { PresetSlotsPopup } from "@point_of_sale/app/components/popups/preset_slots_popup/preset_slots_popup";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { luxon } from "@web/core/l10n/luxon";

definePosModels();

test("loads independent presets together and renders only the selected day", async () => {
    const pos = await setupPosEnv();
    const presets = [pos.models["pos.preset"].get(1), pos.models["pos.preset"].get(2)];
    const now = luxon.DateTime.now();
    const dates = [now.toISODate(), now.plus({ days: 1 }).toISODate()];
    for (const preset of presets) {
        preset.use_timing = true;
        preset.uiState.generatedFor = `${now.toISODate()}/${now.zoneName}`;
        preset.uiState.availabilities = Object.fromEntries(
            dates.map((date, day) => [
                date,
                {
                    "09:00": {
                        datetime: luxon.DateTime.fromISO(date).set({
                            hour: 8 + preset.id + day,
                        }),
                        periode: "morning",
                        isFull: false,
                        order_ids: new Set(),
                    },
                },
            ]),
        );
    }
    pos.addNewOrder({ preset_id: presets[0] });
    const gate = new Deferred();
    const calls = [];
    patchWithCleanup(pos, {
        syncPresetSlotAvaibility(preset) {
            calls.push(preset.id);
            return gate;
        },
    });
    const selected = [];
    const mounting = mountWithCleanup(PresetSlotsPopup, {
        props: {
            close() {},
            getPayload(payload) {
                selected.push(payload);
            },
        },
    });
    await animationFrame();
    expect(calls).toEqual([1, 2]);
    gate.resolve();
    const popup = await mounting;
    expect(".preset-slot-button").toHaveCount(1);
    expect(".preset-slot-button").toHaveText("09:00");
    popup.state.selectedDate = dates[1];
    popup.state.selectedPresetId = 2;
    await animationFrame();
    expect(".preset-slot-button").toHaveCount(1);
    expect(".preset-slot-button").toHaveText("11:00");
    await click(".preset-slot-button");
    expect(selected).toEqual([
        { slot: presets[1].availabilities[dates[1]]["09:00"], presetId: 2 },
    ]);
    popup.state.selectedDate = dates[0];
    presets[1].uiState.availabilities[dates[0]] = {};
    await animationFrame();
    expect(".preset-slot-button").toHaveCount(0);
    expect(".alert-warning").toHaveText("No slot available for this day");
});
