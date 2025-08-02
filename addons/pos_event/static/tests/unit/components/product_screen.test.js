import { describe, expect, test } from "@odoo/hoot";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("pos_event product_screen.js", () => {
    test("addProductToOrder", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();
        const event = models["event.event"].get(1);
        onRpc("event.event", "get_slot_tickets_availability_pos", (data) => [10]);
        const eventProducts = models["product.template"].filter((product) => product._event_id);
        const comp = await mountWithCleanup(ProductScreen, {});
        await comp.addProductToOrder(eventProducts[0]);
        const orderline = order.lines[0];

        expect(order.lines).toHaveLength(1);
        expect(orderline.event_ticket_id.event_id).toEqual(event);
        expect(orderline.event_registration_ids).toHaveLength(1);
        expect(orderline.event_registration_ids[0].id).toBe(event.registration_ids[0].id);
        expect(orderline.event_registration_ids[0].name).toBe("Test User");
        expect(orderline.event_registration_ids[0].email).toBe("test@test.com");
        expect(orderline.event_registration_ids[0].phone).toBe("+911234567890");
        expect(orderline.event_registration_ids[0].event_slot_id).toEqual(event.event_slot_ids[0]);
        expect(orderline.price_subtotal_incl).toBe(event.event_ticket_ids[0].price);
    });
});
