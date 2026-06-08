import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "@pos_stock/../tests/unit/data/generate_model_definitions";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { PosStore } from "@point_of_sale/app/services/pos_store";

definePosStockModels();

test("initLoadState initializes loaded lots flags", async () => {
    const store = await setupPosEnv();

    const state = store.initLoadState();

    expect(state.useLoadedLots).toBe(false);
    expect(state.userWasAskedAboutLoadedLots).toBe(false);
});

test("test_settle_order_with_lot: updateSOLines loads serial numbers when lots are enabled", async () => {
    const store = await setupPosEnv();
    patchWithCleanup(PosStore.prototype, {
        initLoadState() {
            return {
                useLoadedLots: true,
                userWasAskedAboutLoadedLots: true,
            };
        },
    });

    store.addNewOrder();
    const saleOrder = await store._getSaleOrder(31);

    store.dialog.add = (component, props) => {
        if (props.confirm) {
            props.confirm();
        }
    };

    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);

    const lotNames = store
        .getOrder()
        .lines.flatMap((line) => line.pack_lot_ids.map((lotLine) => lotLine.lot_name))
        .sort();
    expect(lotNames).toEqual(["1001", "1002"]);
});

test("test_import_lot_groupable_and_non_groupable: updateSOLines splits non-groupable lot lines and preserves converted price", async () => {
    const store = await setupPosEnv();
    patchWithCleanup(PosStore.prototype, {
        initLoadState() {
            return {
                useLoadedLots: true,
                userWasAskedAboutLoadedLots: true,
            };
        },
    });

    store.addNewOrder();
    const saleOrder = await store._getSaleOrder(32);

    store.dialog.add = (component, props) => {
        if (props.confirm) {
            props.confirm();
        }
    };

    const product = store.models["product.product"].get(26);
    product.uom_id.is_pos_groupable = false;
    product.uom_id.isZero = (qty) => Math.abs(qty) < 1e-6;
    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);
    const order = store.getOrder();

    const lines = order.lines.filter((line) => line.product_id.id === product.id);
    expect(lines).toHaveLength(3);
    expect(lines.map((line) => line.qty)).toEqual([1, 1, 1]);
    expect(lines.map((line) => line.price_unit)).toEqual([12, 12, 12]);
    expect(lines.map((line) => line.discount)).toEqual([15, 15, 15]);
    expect(lines.map((line) => line.pack_lot_ids[0].lot_name)).toEqual(["LOT-1", "LOT-1", "LOT-2"]);
});

test("test_settle_changed_price_with_lots: updateSOLines keeps custom converted price for lot-tracked lines", async () => {
    const store = await setupPosEnv();
    patchWithCleanup(PosStore.prototype, {
        initLoadState() {
            return {
                useLoadedLots: true,
                userWasAskedAboutLoadedLots: true,
            };
        },
    });

    store.addNewOrder();
    const saleOrder = await store._getSaleOrder(33);

    store.dialog.add = (component, props) => {
        if (props.confirm) {
            props.confirm();
        }
    };

    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);
    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].price_unit).toBe(120);
    expect(order.lines[0].pack_lot_ids.map((lotLine) => lotLine.lot_name)).toEqual(["LOT-PRICE"]);
});

test("PosShipLaterNoDefault: settling a sale order keeps ship later inactive by default", async () => {
    const store = await setupPosEnv();
    store.config.ship_later = true;
    const order = store.addNewOrder();
    const saleOrder = await store._getSaleOrder(1);

    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);
    await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    expect(order.shipping_date).toBe(undefined);
    expect(".button:contains('Ship Later')").toHaveCount(1);
    expect(".button.highlight:contains('Ship Later')").toHaveCount(0);
});

test("test_settle_order_with_lot: settling lot-tracked lines loads SN/Lots", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const saleOrder = await store._getSaleOrder(6);
    const product = store.models["product.product"].get(5);
    product.tracking = "lot";

    store.dialog.add = (component, props) => {
        if (props.confirm) {
            props.confirm();
        }
    };

    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);

    const lotNames = store
        .getOrder()
        .lines.map((line) => line.pack_lot_ids[0]?.lot_name)
        .filter((lotName) => lotName)
        .sort();
    expect(lotNames).toEqual(["1001", "1002"]);
});
