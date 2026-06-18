import { test, describe, expect } from "@odoo/hoot";
import {
    setupSelfPosEnv,
    getFilledSelfOrder,
    addComboProduct,
    checkKioskPreparationTicketData,
} from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

describe("preparation ticket", () => {
    test("preparation ticket check 1", async () => {
        const store = await setupSelfPosEnv();
        await getFilledSelfOrder(store);

        const result = await checkKioskPreparationTicketData(store, [
            { name: "TEST", quantity: 3 },
            { name: "TEST 2", quantity: 2 },
        ]);
        expect(result).toBe(true);
    });
    test("preparation ticket check 2 - preparation categories", async () => {
        const store = await setupSelfPosEnv();

        const product1 = store.models["product.template"].get(11); // Steel desk
        const product2 = store.models["product.template"].get(13); // Pizza margarita

        await store.addToCart(product1, 2);
        await store.addToCart(product2, 2);

        const result = await checkKioskPreparationTicketData(store, [
            { name: "Steel desk", quantity: 2 },
        ]);
        expect(result).toBe(true);
    });
    test("preparation ticket check 3 - combo", async () => {
        const store = await setupSelfPosEnv();
        await addComboProduct(store);

        const result = await checkKioskPreparationTicketData(store, [
            { name: "Product combo", quantity: 2 },
            { name: "Wood chair", quantity: 2 },
            { name: "Wood desk", quantity: 2 },
        ]);
        expect(result).toBe(true);
    });
    test("course allocation preparation ticket", async () => {
        const store = await setupSelfPosEnv();
        const foodCourse = store.models["pos.course"].create({
            name: "Food",
            sequence: 1,
        });

        store.config.use_course_allocation = true;
        store.models["pos.category"].get(2).course_id = foodCourse;

        const product = store.models["product.template"].get(11); // Steel desk
        await store.addToCart(product, 1);
        const result = await checkKioskPreparationTicketData(store, [
            {
                name: product.name,
                quantity: 1,
                course: "Food",
            },
        ]);

        expect(result).toBe(true);
    });
});
