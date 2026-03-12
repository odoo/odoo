import { test, expect } from "@odoo/hoot";
import { pointerDown, pointerUp, queryAll, queryOne } from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "../data/generate_model_definitions";
import { LONG_PRESS_DURATION, TOUCH_DELAY } from "@point_of_sale/utils";

definePosModels();

async function mountProductScreen() {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    return { store, order, productScreen };
}

test("_getProductByBarcode", async () => {
    const { store, order, productScreen } = await mountProductScreen();
    await productScreen.addProductToOrder(store.models["product.template"].get(5));

    expect(order.displayPrice).toBe(3.45);
    expect(productScreen.total).toBe("$\u00a03.45");
    expect(productScreen.items).toBe("1");

    const productByBarcode = await productScreen._getProductByBarcode({ base_code: "test_test" });
    expect(productByBarcode.id).toEqual(5);
});

test("fastValidate", async () => {
    const { store, order, productScreen } = await mountProductScreen();
    const fastPaymentMethod = order.config.fast_payment_method_ids[0];
    await productScreen.addProductToOrder(store.models["product.template"].get(5));

    expect(order.displayPrice).toBe(3.45);
    expect(productScreen.total).toBe("$\u00a03.45");
    expect(productScreen.items).toBe("1");

    await productScreen.fastValidate(fastPaymentMethod);

    expect(order.payment_ids[0].payment_method_id).toEqual(fastPaymentMethod);
    expect(order.state).toBe("paid");
    expect(order.amount_paid).toBe(3.45);
});

test("long press on a product opens the product info popup", async () => {
    const { store } = await mountProductScreen();

    patchWithCleanup(store, {
        async onProductInfoClick(product) {
            expect.step(`product-info:${product.id}`);
        },
    });

    const product = queryOne('.product-sortable[data-product-id="5"]');
    await pointerDown(product);
    await advanceTime(LONG_PRESS_DURATION + TOUCH_DELAY + 5);
    await pointerUp(product);
    expect.verifySteps(["product-info:5"]);
});

test("simple click on a product adds it to the cart", async () => {
    const { store, order } = await mountProductScreen();

    patchWithCleanup(store, {
        async onProductInfoClick(product) {
            expect.step(`product-info:${product.id}`);
        },
    });

    await contains('.product-sortable[data-product-id="5"]').click();

    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].product_id.product_tmpl_id.id).toBe(5);
    expect.verifySteps([]);
});

test("drag and drop reorders products", async () => {
    const getRenderedProductIds = () =>
        queryAll(".product-sortable").map((product) => Number(product.dataset.productId));

    const { store } = await mountProductScreen();
    const products = store.models["product.template"];
    const categoryTwoProducts = products
        .getAll()
        .filter((product) => product.pos_categ_ids.some((category) => category.id === 2));

    for (const [index, product] of categoryTwoProducts.entries()) {
        product.update({ is_favorite: false, pos_sequence: 100 + index });
    }
    products.get(6).update({ pos_sequence: 10 });
    products.get(8).update({ pos_sequence: 20 });
    products.get(9).update({ pos_sequence: 30 });
    products.get(7).update({ pos_sequence: 40 });
    store.setSelectedCategory(2);
    await animationFrame();

    onRpc("product.template", "set_pos_sequence", (params) => {
        const sequenceById = params.args[0];
        for (const [id, seq] of Object.entries(sequenceById)) {
            expect.step(`product.template:${id}:${seq}`);
        }
        return true;
    });

    const initialRenderedIds = getRenderedProductIds();
    expect(initialRenderedIds.indexOf(6)).toBeLessThan(initialRenderedIds.indexOf(8));
    expect(initialRenderedIds.indexOf(8)).toBeLessThan(initialRenderedIds.indexOf(9));
    expect(initialRenderedIds.indexOf(9)).toBeLessThan(initialRenderedIds.indexOf(7));

    await contains('.product-sortable[data-product-id="6"]').dragAndDrop(
        '.product-sortable[data-product-id="8"]'
    );
    await animationFrame();

    expect.verifySteps(["product.template:6:21"]);
    const reorderedIds = getRenderedProductIds();
    expect(reorderedIds.indexOf(8)).toBeLessThan(reorderedIds.indexOf(6));
    expect(reorderedIds.indexOf(6)).toBeLessThan(reorderedIds.indexOf(9));
    expect(reorderedIds.indexOf(9)).toBeLessThan(reorderedIds.indexOf(7));
    expect(products.get(6).pos_sequence).toBe(21);
});
