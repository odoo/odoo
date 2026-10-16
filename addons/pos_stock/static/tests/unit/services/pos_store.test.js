import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosStockModels } from "@pos_stock/../tests/unit/data/generate_model_definitions";

definePosStockModels();

const setupLotProduct = (store) => {
    const product = store.models["product.product"].get(5);
    product.tracking = "lot";
    product.product_tmpl_id.tracking = "lot";
    return product;
};

test("addLineToCurrentOrder asks the lot of a tracked product", async () => {
    const store = await setupPosEnv();
    const product = setupLotProduct(store);
    patchWithCleanup(store, {
        editLots: async () => ({
            modifiedPackLotLines: {},
            newPackLotLines: [{ lot_name: "LOT001" }],
        }),
    });

    const line = await store.addLineToCurrentOrder({ product_tmpl_id: product.product_tmpl_id });
    expect(line.pack_lot_ids.map((lot) => lot.lot_name)).toEqual(["LOT001"]);
});

test("addLineToCurrentOrder adds nothing when the lot selection is cancelled", async () => {
    const store = await setupPosEnv();
    const product = setupLotProduct(store);
    patchWithCleanup(store, { editLots: async () => undefined });

    const line = await store.addLineToCurrentOrder({ product_tmpl_id: product.product_tmpl_id });
    expect(line).toBe(undefined);
    expect(store.getOrder().lines).toHaveLength(0);
});
