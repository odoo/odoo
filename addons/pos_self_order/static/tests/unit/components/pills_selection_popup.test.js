import { test, expect, mockDate } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { PillsSelectionPopup } from "@pos_self_order/app/components/pills_selection_popup/pills_selection_popup";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("PillsSelectionPopup", async () => {
    mockDate("2026-05-15 12:00:00");
    const store = await setupSelfPosEnv();
    const preset = store.models["pos.preset"].get(2);
    store.currentOrder.preset_id = preset;

    await mountWithCleanup(PillsSelectionPopup, {
        props: {
            options: store.getTimingOptions(preset),
            title: "Select Time",
            subtitle: "Choose when to receive your order",
            close: () => {},
            getPayload: () => {},
            selectionType: "time",
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
        { label: "Tuesday", date: "May 19" },
        { label: "Wednesday", date: "May 20" },
        { label: "Thursday", date: "May 21" },
    ]);
});
