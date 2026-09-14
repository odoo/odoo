import { expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { definePosModels } from "../data/generate_model_definitions.js";
import { getFilledOrder, setupPosEnv } from "../utils.js";

definePosModels();

for (const [start, cancel] of [
    ["mousedown", "mouseleave"],
    ["touchstart", "touchcancel"],
]) {
    test(`${cancel} on a product card cancels its information popup`, async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        store.onProductInfoClick = () => expect.step("product info");
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
        const card = getFixture().querySelector(".product[data-product-id='5']");
        card.dispatchEvent(
            start === "mousedown"
                ? new MouseEvent(start, { bubbles: true, button: 0 })
                : new Event(start, { bubbles: true }),
        );
        card.dispatchEvent(new Event(cancel, { bubbles: cancel !== "mouseleave" }));
        await advanceTime(1000);
        expect.verifySteps([]);
    });
}

test("moving between children of a product card does not cancel its long press", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    store.onProductInfoClick = () => expect.step("product info");
    await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
    const card = getFixture().querySelector(".product[data-product-id='5']");
    const label = card.querySelector(".product-name");
    label.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, button: 0 }));
    label.dispatchEvent(new MouseEvent("mouseleave", { relatedTarget: card }));
    await advanceTime(1000);
    expect.verifySteps(["product info"]);
});

test("cart badges follow quantity transfers even when the order total is unchanged", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
    await animationFrame();
    const badge = (id) => `.product[data-product-id='${id}'] .product-cart-qty`;
    expect(badge(5)).toHaveText("3");
    expect(badge(6)).toHaveText("2");
    order.lines[0].setQuantity(2);
    order.lines[1].setQuantity(3);
    await animationFrame();
    await animationFrame();
    expect(badge(5)).toHaveText("2");
    expect(badge(6)).toHaveText("3");
});

test("cart badges follow product replacement without a quantity change", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
    await animationFrame();
    order.lines[0].update({ product_id: store.models["product.product"].get(6) });
    await animationFrame();
    await animationFrame();
    expect(".product[data-product-id='5'] .product-cart-qty").toHaveCount(0);
    expect(".product[data-product-id='6'] .product-cart-qty").toHaveText("5");
});

test("changing orders with the same total updates the card quantities", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
    const nextOrder = await getFilledOrder(store);
    nextOrder.lines[0].setQuantity(1);
    nextOrder.lines[1].setQuantity(4);
    await animationFrame();
    await animationFrame();
    expect(".product[data-product-id='5'] .product-cart-qty").toHaveText("1");
    expect(".product[data-product-id='6'] .product-cart-qty").toHaveText("4");
});

test("_getProductByBarcode", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const comp = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addProductToOrder(store.models["product.template"].get(5));

    expect(order.displayPrice).toBe(3.45);
    expect(comp.total).toBe("$\u00a03.45");
    expect(comp.items).toBe("1");

    const productByBarcode = await comp._getProductByBarcode({
        base_code: "test_test",
    });
    expect(productByBarcode.id).toEqual(5);
});

test("fastValidate", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const fastPaymentMethod = order.config.fast_payment_method_ids[0];
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    await productScreen.addProductToOrder(store.models["product.template"].get(5));

    expect(order.displayPrice).toBe(3.45);
    expect(productScreen.total).toBe("$\u00a03.45");
    expect(productScreen.items).toBe("1");

    await productScreen.fastValidate(fastPaymentMethod);

    expect(order.payment_ids[0].payment_method_id).toEqual(fastPaymentMethod);
    expect(order.state).toBe("paid");
    expect(order.amount_paid).toBe(3.45);
});
