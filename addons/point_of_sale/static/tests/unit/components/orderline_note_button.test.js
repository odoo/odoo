import { expect, test } from "@odoo/hoot";
import { setupPosEnv, dialogActions } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { click } from "@odoo/hoot-dom";
import { InternalNoteButton } from "@point_of_sale/app/screens/product_screen/control_buttons/orderline_note_button/orderline_note_button";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

definePosModels();

test("orderline_note_button.js", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const productTmplCombo = store.models["product.template"].get(7);

    const productComboSteps = [
        () => click("#article_product_8"), // Wood Chair 1/2
        () => click("#article_product_8"), // Wood Chair 2/2
        () => click("#article_product_10"), // Wood desk
        () => click(".confirm"), // Confirm combo configuration
    ];
    const lineAction = async () =>
        await store.addLineToCurrentOrder({
            product_tmpl_id: productTmplCombo,
            qty: 1,
        });
    const line = await dialogActions(lineAction, productComboSteps);
    expect(order.lines[0].qty).toBe(1);
    expect(order.lines[1].qty).toBe(1);
    expect(order.lines[2].qty).toBe(2);
    const orderSummary = await mountWithCleanup(OrderSummary, { props: {} });
    orderSummary._setValue(4);
    expect(order.lines[0].qty).toBe(4);
    expect(order.lines[1].qty).toBe(4);
    expect(order.lines[2].qty).toBe(8);
    const comp = await mountWithCleanup(InternalNoteButton, { props: { label: "" } });
    await comp.setChanges(line, '[{"1":"Test","colorIndex":0}]');
    order.updateLastOrderChange();
    orderSummary._setValue(9);

    const noteAction = async () => await comp.setChanges(line, '[{"2":"Test","colorIndex":0}]');
    await dialogActions(noteAction, productComboSteps);
    // Check quantity
    expect(order.lines[0].qty).toBe(4);
    expect(order.lines[1].qty).toBe(4);
    expect(order.lines[2].qty).toBe(8);
    expect(order.lines[3].qty).toBe(5);
    expect(order.lines[4].qty).toBe(5);
    expect(order.lines[5].qty).toBe(10);

    // Check notes (only on parent lines)
    expect(order.lines[0].note).toBe('[{"1":"Test","colorIndex":0}]');
    expect(order.lines[3].note).toBe('[{"2":"Test","colorIndex":0}]');
});
