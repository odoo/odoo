import { expect, test } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { EventConfiguratorPopup } from "@pos_event/app/components/popup/event_configurator_popup/event_configurator_popup";
import { EventRegistrationPopup } from "@pos_event/app/components/popup/event_registration_popup/event_registration_popup";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("test_selling_multiple_ticket_saved: addProductToOrder creates event lines and registrations", async () => {
    const store = await setupPosEnv();
    store.session.state = "opened";
    const order = store.addNewOrder();
    const product = store.models["product.template"].get("dummy_5");
    const tickets = [
        store.models["event.event.ticket"].get(5),
        store.models["event.event.ticket"].create({
            id: 6,
            name: "Extra Limited Ticket",
            event_id: product.event_id,
            product_id: store.models["product.product"].get(106),
            seats_available: 3,
            seats_max: 5,
            price: 100,
        }),
    ];
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });

    patchWithCleanup(productScreen.dialog, {
        add(component, props) {
            if (component === EventConfiguratorPopup) {
                props.getPayload(
                    tickets.map((ticket) => ({
                        product_id: ticket.product_id,
                        ticket_id: ticket,
                        qty: 1,
                    }))
                );
            } else if (component === EventRegistrationPopup) {
                props.getPayload({
                    byRegistration: Object.fromEntries(tickets.map((ticket) => [ticket.id, [{}]])),
                    byOrder: {},
                });
            }
        },
    });

    await productScreen.addProductToOrder(product);

    expect(order.lines).toHaveLength(2);
    expect(order.lines.map((line) => line.event_ticket_id)).toEqual(tickets);
    for (const line of order.lines) {
        expect(line.event_registration_ids).toHaveLength(1);
        expect(line.event_registration_ids[0].event_id).toEqual(product.event_id);
    }
});

test("test_selling_multiple_ticket_saved: extractRegistrationData splits attendee data from answers", async () => {
    const store = await setupPosEnv();
    store.session.state = "opened";
    const order = store.addNewOrder();
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    const data = productScreen.extractRegistrationData(
        {
            1: "Ada",
            2: "ada@example.com",
            3: "",
            4: "1",
        },
        { phone: "+321" }
    );

    expect(data.userData).toEqual({
        name: "Ada",
        email: "ada@example.com",
        phone: "+321",
    });
    expect(data.textAnswer).toEqual({
        1: "Ada",
        2: "ada@example.com",
        4: "1",
    });
});
