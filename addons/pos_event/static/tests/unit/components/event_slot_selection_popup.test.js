import { expect, test } from "@odoo/hoot";
import { EventSlotSelectionPopup } from "@pos_event/app/components/popup/event_slot_selection_popup/event_slot_selection_popup";
import { mountPosDialog, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { click } from "@odoo/hoot-dom";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("confirm payload", async () => {
    const store = await setupPosEnv();
    const event = store.models["event.event"].get(1);
    let payload = [];
    const comp = await mountPosDialog(EventSlotSelectionPopup, {
        event: event,
        availabilityPerSlot: [event.event_slot_ids[0].id, 10],
        getPayload: (data) => {
            payload = data;
        },
        close: () => {},
    });

    await click(`button.o_event_slot_btn`);
    comp.confirm();

    expect(payload).toHaveLength(3);
    expect(payload).toEqual({
        slotAvailability: 10,
        slotId: 1,
        slotName: "Mar 11 2019, Monday, 12:00 PM",
    });
});
