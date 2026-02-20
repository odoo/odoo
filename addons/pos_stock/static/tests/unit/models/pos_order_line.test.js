import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "@pos_stock/../tests/unit/data/generate_model_definitions";

definePosStockModels();

test("[canBeMergedWith]: Base test", async () => {
    // // Test with lot tracking
    const store = await setupPosEnv();
    const lotOrder = await getFilledOrder(store);
    const [lotLine1, lotLine2] = lotOrder.lines;
    lotLine2.product_id = lotLine1.product_id; // same product
    lotLine2.product_id.tracking = "lot";
    lotLine2.setFullProductName("TEST"); // same name
    const lot1 = store.models["pos.pack.operation.lot"].create({
        lot_name: "LOT001",
        pos_order_line_id: lotLine1,
    });
    const lot2 = store.models["pos.pack.operation.lot"].create({
        lot_name: "LOT001",
        pos_order_line_id: lotLine2,
    });
    lotLine1.pack_lot_ids = [lot1];
    lotLine2.pack_lot_ids = [lot2];
    expect(lotLine1.canBeMergedWith(lotLine2)).toBe(true);
    lotLine1.merge(lotLine2);
    expect(lotLine1.qty).toBe(5);
    expect(lotLine1.pack_lot_ids.length).toBe(1);

    // Test with different lots, should not merge
    lot2.lot_name = "LOT002";
    expect(lotLine1.canBeMergedWith(lotLine2)).toBe(false);
});
