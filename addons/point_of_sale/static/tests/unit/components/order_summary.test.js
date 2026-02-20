import { test, expect, animationFrame } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { setupPosEnv, getFilledOrder } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryAll, queryOne } from "@odoo/hoot-dom";

definePosModels();

test("getNewLine", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const orderSummary = await mountWithCleanup(OrderSummary, {});
    order.getSelectedOrderline().uiState.savedQuantity = 5;
    const newLine = orderSummary.getNewLine();
    expect(newLine.order_id.id).toBe(order.id);
    expect(newLine.qty).toBe(0);
});

test("Display tax include/exclude subtotal label", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    order.config.iface_tax_included = "total";
    await mountWithCleanup(OrderSummary, {});
    const total = queryOne(".total");
    const subtotal = queryAll(".subtotal");
    expect(subtotal).toHaveLength(0);
    expect(total.innerHTML).toBe("$&nbsp;17.85");

    order.config.iface_tax_included = "subtotal";
    await animationFrame();
    const total2 = queryOne(".total");
    const subtotal2 = queryOne(".subtotal");
    expect(total2.innerHTML).toBe("$&nbsp;17.85");
    expect(subtotal2.innerHTML).toBe("$&nbsp;15.00");
});

test("price_type check on manual price edit", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product1 = store.models["product.template"].get(5);

    await store.addLineToCurrentOrder({ product_tmpl_id: product1 });
    expect(order.lines[0].price_type).toBe("original");

    store.numpadMode = "price";
    const orderSummary = await mountWithCleanup(OrderSummary, {});
    orderSummary._setValue(5);
    expect(order.lines[0].qty).toBe(1);
    expect(order.lines[0].price_unit).toBe(5);
    expect(order.lines[0].price_type).toBe("override");

    await store.addLineToCurrentOrder({ product_tmpl_id: product1 });
    expect(order.lines).toHaveLength(2);
    expect(order.lines[1].qty).toBe(1);
    expect(order.lines[1].price_unit).toBe(3);
    expect(order.lines[1].price_type).toBe("original");
});
