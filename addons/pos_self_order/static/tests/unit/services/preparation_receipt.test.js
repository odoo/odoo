import { test, describe, expect } from "@odoo/hoot";
import { setupSelfPosEnv, getFilledSelfOrder, addComboProduct } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { checkKioskPreparationTicketData } from "../preparation_receipt_util";

definePosSelfModels();

describe("preparation ticket", () => {
    test("preparation ticket check 1", async () => {
        const store = await setupSelfPosEnv();
        await getFilledSelfOrder(store);

        const result = checkKioskPreparationTicketData(
            store,
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
    test("preparation ticket check 2 - preparation categories", async () => {
        const store = await setupSelfPosEnv();

        const product1 = store.models["product.template"].get(11); // Steel desk
        const product2 = store.models["product.template"].get(13); // Pizza margarita

        await store.addToCart(product1, 2);
        await store.addToCart(product2, 2);

        const result = checkKioskPreparationTicketData(store, [{ name: "Steel desk", qty: 2 }], {
            invisibleInDom: ["Pizza margarita"],
        });
        expect(result).toBe(true);
    });
    test("preparation ticket check 3 - combo", async () => {
        const store = await setupSelfPosEnv();
        await addComboProduct(store);

        const result = checkKioskPreparationTicketData(store, [
            { name: "Product combo", qty: 2 },
            { name: "Wood desk", qty: 2 },
            { name: "Wood chair", qty: 2 },
        ]);
        expect(result).toBe(true);
    });
});
