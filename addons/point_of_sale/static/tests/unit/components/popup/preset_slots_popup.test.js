import { test, expect, mockDate } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { PresetSlotsPopup } from "@point_of_sale/app/components/popups/preset_slots_popup/preset_slots_popup";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("PresetSlotsPopup", async () => {
    mockDate("2026-05-15 12:00:00");
    const store = await setupPosEnv();
    store.addNewOrder({ preset_id: store.models["pos.preset"].get(2) });

    await mountWithCleanup(PresetSlotsPopup, {
        props: {
            close: () => {},
            getPayload: () => {},
        },
    });

    const buttons = [...document.querySelectorAll(".preset_date_buttons")];
    const result = buttons.map((btn) => ({
        label: btn.querySelector("span")?.textContent?.trim(),
        date: btn.querySelector("small")?.textContent?.trim() || null,
    }));

    expect(result).toEqual([
        { label: "Today", date: null },
        { label: "Tomorrow", date: null },
        { label: "Sunday", date: "May 17" },
        { label: "Monday", date: "May 18" },
        { label: "Tuesday", date: "May 19" },
        { label: "Wednesday", date: "May 20" },
        { label: "Thursday", date: "May 21" },
    ]);
});
