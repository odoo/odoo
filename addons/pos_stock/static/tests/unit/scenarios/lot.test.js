import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "@pos_stock/../tests/unit/data/generate_model_definitions";

definePosStockModels();

test("test_lot_tracking_without_lot_creation: with lot tracking and without lot creation orderlines will merge", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const lotProductTemplate = store.models["product.template"].get(25);
    store.models["stock.picking.type"].getFirst().update({
        use_create_lots: false,
        use_existing_lots: false,
    });

    const firstLine = await store.addLineToOrder(
        {
            product_tmpl_id: lotProductTemplate,
            qty: 1,
        },
        order,
        {},
        false
    );

    expect(firstLine.isLotTracked()).toBe(false);

    await store.addLineToOrder(
        {
            product_tmpl_id: lotProductTemplate,
            qty: 1,
        },
        order,
        {},
        false
    );
    expect(order.lines.length).toBe(1);
});

test("test_combo_price_unchanged_with_lot_tracked_product: combo price unchanged with lot tracked product", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const comboTemplate = store.models["product.template"].get(7);
    const comboItem = store.models["product.combo.item"].get(1);

    await store.addLineToCurrentOrder({
        product_tmpl_id: comboTemplate,
        payload: [[{ combo_item_id: comboItem, qty: 1 }]],
        qty: 1,
    });

    order.setOrderPrices();
    const totalBefore = order.prices.taxDetails.total_amount;

    const comboChildLine = order.lines.find((line) => line.combo_parent_id);
    comboChildLine.product_id.product_tmpl_id.tracking = "lot";
    const lot = store.models["pos.pack.operation.lot"].create({
        lot_name: "Lot Number 1",
        pos_order_line_id: comboChildLine,
    });
    comboChildLine.pack_lot_ids = [lot];

    order.setOrderPrices();
    const totalAfter = order.prices.taxDetails.total_amount;

    expect(totalAfter).toBe(totalBefore);
});

test("test_order_with_existing_serial: order with existing serial keeps serial lines", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const serialTemplate = store.models["product.template"].get(26);
    store.configureNewOrderLine = async () => ({
        modifiedPackLotLines: {},
        newPackLotLines: [{ id: "246fdb39-6e82-4801-ad90-9ad44a5d4be9", lot_name: "SN1" }],
    });
    const line = await store.addLineToOrder(
        {
            product_tmpl_id: serialTemplate,
            qty: 1,
            pack_lot_ids: [["create", { lot_name: "SN1" }]],
        },
        order,
        {}
    );

    line.setPackLotLines({
        modifiedPackLotLines: { [line.pack_lot_ids[0].id]: "SN1" },
        newPackLotLines: [{ id: "246fdb39-6e82-4801-ad90-9ad44a5d4be5", lot_name: "SN2" }],
        setQuantity: true,
    });

    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].id).toBe(line.id);
    expect(order.lines[0].qty).toBe(2);
    expect(order.lines[0].pack_lot_ids.map((l) => l.lot_name).sort()).toEqual(["SN1", "SN2"]);
});
