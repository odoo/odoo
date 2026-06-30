import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { setupSelfPosEnv } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";

definePosSelfModels();

test("ticketAvailabilityText", async () => {
    const store = await setupSelfPosEnv();
    const eventProduct = store.models["product.template"].get("dummy_1");
    const event = eventProduct.event_id;
    const comp = await mountWithCleanup(ProductCard, {
        props: { product: eventProduct },
    });

    expect(comp.ticketAvailabilityText).toBe("1 slots available");
    event.event_slot_ids = [];
    event.seats_available = 5;
    expect(comp.ticketAvailabilityText).toBe("5 seats available");
    event.seats_available = 0;
    expect(comp.ticketAvailabilityText).toBe("Sold out");
    event.seats_limited = false;
    event.event_ticket_ids.forEach((ticket) => {
        ticket.seats_max = 0;
        ticket.seats_available = 0;
    });
    expect(comp.ticketAvailabilityText).toBe("Unlimited Seats");
});

test("selectProduct", async () => {
    const store = await setupSelfPosEnv();
    store.computeAvailableCategories();
    const product = store.models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductCard, {
        props: { product: product },
    });

    comp.selectProduct();
    expect(store.currentOrder.lines).toHaveLength(1);
    expect(store.currentOrder.lines[0].product_id.id).toBe(5);

    // Event Product
    product._event_id = 1;
    comp.selectProduct();
    // Should not add event product to cart; should navigate to event page
    expect(store.currentOrder.lines).toHaveLength(1);
});
