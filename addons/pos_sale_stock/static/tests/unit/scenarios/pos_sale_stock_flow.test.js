import { expect, test } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "@pos_stock/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as SaleUiUtils from "@pos_sale/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...SaleUiUtils };

definePosStockModels();

function lotNamesOf(order) {
    return order.lines
        .flatMap((line) => line.pack_lot_ids.map((packLot) => packLot.lot_name))
        .sort();
}

test("test_settle_order_with_lot: the SN/Lots of the sale order are loaded on the settled line", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00031", { loadSN: true });

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].qty).toBe(2);
    expect(lotNamesOf(order)).toEqual(["1001", "1002"]);
});

test("test_multiple_lots_sale_order_2: discarding the SN/Lots leaves the line without lot", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00034", { loadSN: false });

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(lotNamesOf(order)).toEqual([]);
    expect(order.lines[0].hasValidProductLot()).toBe(false);
    expect(".order-container .orderline .line-lot-icon.text-danger").toHaveCount(1);
});

test("test_import_lot_groupable_and_non_groupable / test_multiple_lots_sale_order_3: a non groupable lot line is split per lot", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00032", { loadSN: true });

    const order = store.getOrder();
    expect(order.lines).toHaveLength(3);
    expect(order.lines.map((line) => line.qty)).toEqual([1, 1, 1]);
    expect(order.lines.map((line) => line.price_unit)).toEqual([10, 10, 10]);
    expect(order.lines.map((line) => line.pack_lot_ids[0].lot_name)).toEqual([
        "LOT-1",
        "LOT-1",
        "LOT-2",
    ]);
});

test("test_settle_changed_price_with_lots: the price of a lot tracked line is not reset", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00033", { loadSN: true });

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].price_unit).toBe(120);
    expect(lotNamesOf(order)).toEqual(["LOT-PRICE"]);
});

test("test_settle_groupable_lot_total_amount: a groupable lot tracked line keeps its total", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00034", { loadSN: true });

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.priceIncl).toBe(12);
    expect(lotNamesOf(order)).toEqual(["1001"]);
});

test("PosShipLaterNoDefault: settling a sale order does not activate ship later", async () => {
    const store = await setupAndMountPosApp({ ship_later: true });

    await Utils.settleSaleOrder("S00001");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    expect(store.getOrder().shipping_date).toBeEmpty();
    expect(`.button:contains("Ship Later")`).toHaveCount(1);
    expect(`.button.highlight:contains("Ship Later")`).toHaveCount(0);
});

test("PosSettleOrder4 / PosSettleOrderShipLater: ship later sets the shipping date of the order", async () => {
    const store = await setupAndMountPosApp({ ship_later: true });

    await Utils.settleSaleOrder("S00001");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    await contains(`.button:contains("Ship Later")`).click();
    await waitFor(".modal");
    await click(`.modal .btn:contains("Confirm")`);
    await animationFrame();

    expect(store.getOrder().shipping_date).not.toBeEmpty();
    expect(`.button.highlight:contains("Ship Later")`).toHaveCount(1);
});
