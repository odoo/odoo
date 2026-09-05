import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { onRpc } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as EventUiUtils from "@pos_event/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...EventUiUtils };

definePosModels();

test("CheckEventTicketPrice: pricelists apply to event ticket lines", async () => {
    mockDate("2019-03-10 12:00:00");
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const special = Utils.createFixedPricelist(store, {
        id: 40,
        name: "Special Pricelist",
        productId: 106,
        price: 60,
    });
    const standard = Utils.createFixedPricelist(store, {
        id: 41,
        name: "Test Pricelist",
        productId: 106,
        price: 200,
    });
    store.config.available_pricelist_ids = [special, standard];
    store.config.use_pricelist = true;

    await Utils.clickDisplayedProduct("Normal Event");
    await waitFor(".modal .o_event_configurator_popup");
    await Utils.increaseTicketQty("Limited Ticket");
    await Utils.confirmEventPopup();
    await waitFor(".product-screen");
    expect(store.getOrder().lines).toHaveLength(1);
    expect(Utils.getOrderTotal()).toInclude("100.00");

    await Utils.clickPricelist("Special Pricelist");
    expect(Utils.getOrderTotal()).toInclude("60.00");

    await Utils.clickDisplayedProduct("Normal Event");
    await waitFor(".modal .o_event_configurator_popup");
    await Utils.increaseTicketQty("Limited Ticket");
    await Utils.confirmEventPopup();
    await waitFor(".product-screen");
    expect(Utils.getOrderTotal()).toInclude("120.00");

    await Utils.clickPricelist("Test Pricelist");
    expect(Utils.getOrderTotal()).toInclude("400.00");
});

test("test_multislot_unlimited_qty: an unlimited multi-slot event can be sold", async () => {
    mockDate("2019-03-10 12:00:00");
    onRpc("event.event", "get_slot_tickets_availability_pos", () => [null]);
    const store = await setupAndMountPosApp();

    await Utils.clickDisplayedProduct("Unlimited Multi Slot Event");
    await waitFor(".modal .o_event_slot_btn");
    await Utils.selectSlot("12:00");
    await Utils.confirmEventPopup();

    await waitFor(".modal .o_event_configurator_popup");
    expect(Utils.ticketAvailabilityText("Unlimited Slot Ticket")).toInclude("Unlimited");
    await Utils.increaseTicketQty("Unlimited Slot Ticket");
    await Utils.confirmEventPopup();

    await waitFor(".modal .o_event_registration_popup");
    await Utils.confirmEventPopup();

    await waitFor(".product-screen");
    expect(store.getOrder().lines).toHaveLength(1);
    const line = store.getOrder().lines[0];
    expect(line.event_ticket_id.id).toBe(6);
    expect(line.qty).toBe(1);
    expect(line.event_registration_ids).toHaveLength(1);
    expect(line.event_registration_ids[0].event_slot_id.id).toBe(2);
});
