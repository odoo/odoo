import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("getAllChildren", async () => {
    const store = await setupPosEnv();
    const category = store.models["pos.category"].get(3);
    const children = category.getAllChildren();
    expect(children.map((c) => c.id).sort()).toEqual([3, 4, 5]);
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
    expect(associatedProducts.map((p) => p.id).sort()).toEqual([12, 13, 14]);
});
