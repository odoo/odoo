/** @odoo-module **/

import { test, describe, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { setupSelfPosEnv } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";

definePosSelfModels();

describe("ProductListPage", () => {
    test("ticketAvailabilityText", async () => {
        await setupSelfPosEnv();
        const comp = await mountWithCleanup(ProductListPage);

        const product1 = {
            event_id: {
                event_slot_ids: [1, 2, 3],
            },
        };
        expect(comp.ticketAvailabilityText(product1)).toBe("3 slots available");

        const product2 = {
            event_id: {
                seats_limited: false,
                seats_available: 0,
                event_ticket_ids: [{ seats_max: 0 }, { seats_max: 0 }],
            },
        };
        expect(comp.ticketAvailabilityText(product2)).toBe("Unlimited Seats");

        const product3 = {
            event_id: {
                seats_limited: true,
                seats_available: 5,
                event_ticket_ids: [{ seats_available: 3 }, { seats_available: 2 }],
            },
        };
        expect(comp.ticketAvailabilityText(product3)).toBe("5 seats available");

        const product5 = {
            event_id: {
                seats_limited: true,
                seats_available: 0,
                event_ticket_ids: [{ seats_available: 0 }, { seats_available: 0 }],
            },
        };
        expect(comp.ticketAvailabilityText(product5)).toBe("Sold out");
    });

    test("selectProduct", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const comp = await mountWithCleanup(ProductListPage);
        comp.flyToCart = () => {};

        const product = models["product.template"].get(5);
        comp.selectProduct(product);
        expect(store.currentOrder.lines).toHaveLength(1);
        expect(store.currentOrder.lines[0].product_id.id).toBe(5);

        // Event Product
        product._event_id = 1;
        comp.selectProduct(product);
        // Should not add event product to cart; should navigate to event page
        expect(store.currentOrder.lines).toHaveLength(1);
    });
});
