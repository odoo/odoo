import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

describe("pos.category", () => {
    test("getAllChildren", async () => {
        const store = await setupPosEnv();
        const category = store.models["pos.category"].get(3);
        const children = category.getAllChildren();
        expect(children).toEqual([
            store.models["pos.category"].get(3),
            store.models["pos.category"].get(4),
            store.models["pos.category"].get(5),
        ]);
    });

    test("get allParents", async () => {
        const store = await setupPosEnv();
        const category = store.models["pos.category"].get(5);
        const parent = category.allParents;
        expect(parent[0].id).toEqual(3);
    });

    test("get associatedProducts", async () => {
        const store = await setupPosEnv();
        const category = store.models["pos.category"].get(3);
        const associatedProducts = category.associatedProducts;
        expect(associatedProducts).toEqual([
            store.models["product.template"].get(14),
            store.models["product.template"].get(12),
            store.models["product.template"].get(13),
        ]);
    });
});
