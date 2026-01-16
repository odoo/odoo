import { test, expect } from "@odoo/hoot";
import { setupSelfPosEnv, getFilledSelfOrder, addComboProduct } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { TestReceiptUtil } from "@point_of_sale/../tests/unit/test_receipt_helper";

definePosSelfModels();

test("[preparation ticket] check 1", async () => {
    const store = await setupSelfPosEnv();
    await getFilledSelfOrder(store);

    const receipt = new TestReceiptUtil(store, store.currentOrder, "preparation");
    await receipt.generateReceiptToTest();
    const result = receipt.check(
        [
            { name: "TEST", qty: 3 },
            { name: "TEST 2", qty: 2 },
        ],
        {
            visibleInDom: ["NEW"],
            invisibleInDom: ["[]"],
        }
    );
    expect(result).toBe(true);
});
test("[preparation ticket] check 2 - preparation categories", async () => {
    const store = await setupSelfPosEnv();

    const product1 = store.models["product.template"].get(11); // Steel desk
    const product2 = store.models["product.template"].get(13); // Pizza margarita

    await store.addToCart(product1, 2);
    await store.addToCart(product2, 2);

    const receipt = new TestReceiptUtil(store, store.currentOrder, "preparation");
    await receipt.generateReceiptToTest();
    const result = receipt.check([{ name: "Steel desk", qty: 2 }], {
        invisibleInDom: ["Pizza margarita"],
    });
    expect(result).toBe(true);
});
test("[preparation ticket] check 3 - combo", async () => {
    const store = await setupSelfPosEnv();
    await addComboProduct(store);

    const receipt = new TestReceiptUtil(store, store.currentOrder, "preparation");
    await receipt.generateReceiptToTest();
    const result = receipt.check([
        { name: "Product combo", qty: 2 },
        { name: "Wood desk", qty: 2 },
        { name: "Wood chair", qty: 2 },
    ]);
    expect(result).toBe(true);
});
test("[preparation ticket] check 4 - customer note", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    order.general_customer_note = "Test-P Order General Customer Note";

    const receipt = new TestReceiptUtil(store, store.currentOrder, "preparation");
    await receipt.generateReceiptToTest();
    const result = receipt.check(
        [],
        {
            visibleInDom: ["Test-P Order General Customer Note"],
            nbPrints: 2,
        },
        2
    );
    expect(result).toBe(true);
});

test("selfOrder: order receipt validation", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    order.general_customer_note = "Test-P Order General Customer Note";

    const receipt = new TestReceiptUtil(store);
    await receipt.generateReceiptToTest();
    const result = receipt.check(
        [
            { name: "TEST", qty: 3, price: 345 },
            { name: "TEST 2", qty: 2, price: 250 },
        ],
        {
            visibleInDom: ["Test-P Order General Customer Note"],
            nbPrints: 1,
        }
    );
    expect(result).toBe(true);
});
