import { expect, queryAll, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { MockServer } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as SaleUiUtils from "@pos_sale/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...SaleUiUtils };

definePosModels();

test("PosSettleOrder: settle a sale order, change a quantity and pay", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00001");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(3);
    expect(Utils.hasOrderline({ productName: "TEST", quantity: "5" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "TEST 2", quantity: "3" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Productless Line", quantity: "2" })).toBe(true);

    await Utils.clickOrderline("TEST 2");
    await Utils.sendBufferKeys("2");
    expect(Utils.hasOrderline({ productName: "TEST 2", quantity: "2" })).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();

    expect(order.state).toBe("paid");
});

test("PosSettleOrderIncompatiblePartner: settling an order of another customer starts a new order", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00001");
    const firstOrder = store.getOrder();
    expect(firstOrder.getPartner().id).toBe(3);

    await Utils.settleSaleOrder("S00006");
    const secondOrder = store.getOrder();

    expect(secondOrder.id).not.toBe(firstOrder.id);
    expect(secondOrder.getPartner().id).toBe(4);
    expect(secondOrder.lines).toHaveLength(1);
    expect(secondOrder.lines[0].price_unit).toBe(11);
});

test("PosSettleDraftOrder: settling a quotation loads its line", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00005");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].qty).toBe(1);
    expect(order.lines[0].price_unit).toBe(50);
    expect(Utils.hasOrderline({ productName: "TEST", quantity: "1" })).toBe(true);
});

test("PosSettleCustomPrice: changing the customer keeps the sale order line price", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00001");
    const line = store.getOrder().lines[0];
    expect(line.price_unit).toBe(100);

    await Utils.selectCustomer("User1");

    expect(store.getOrder().getPartner().id).toBe(4);
    expect(line.price_unit).toBe(100);
});

test("test_settle_so_with_non_pos_groupable_uom: quantity is converted back to the product unit", async () => {
    const store = await setupAndMountPosApp();

    // "Pomme de Terre" is sold in kg, a unit that is not groupable in the PoS.
    await Utils.settleSaleOrder("S00008");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].product_id.uom_id.is_pos_groupable).toBe(false);
    expect(order.lines[0].qty).toBe(0.5);
    expect(order.lines[0].price_unit).toBe(10);
    expect(Utils.hasOrderline({ productName: "Pomme de Terre", quantity: "0.5" })).toBe(true);
});

test("test_quantity_updated_settle: settling twice only loads the remaining quantity", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00009");
    const firstOrder = store.getOrder();
    expect(firstOrder.lines[0].qty).toBe(5);

    // The settled line is the selected one.
    await Utils.sendBufferKeys("2");
    expect(firstOrder.lines[0].qty).toBe(2);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();

    // The delivered quantity of the sale order line is updated by the backend
    // once the settled order is paid.
    MockServer.env["sale.order.line"].write([12], { qty_delivered: 2 });

    await Utils.settleSaleOrder("S00009");
    const secondOrder = store.getOrder();
    expect(secondOrder.id).not.toBe(firstOrder.id);
    expect(secondOrder.lines[0].qty).toBe(3);
    expect(secondOrder.lines[0].price_unit).toBe(11.5);
});

test("PoSApplyDownpayment / PoSDownPaymentAmount: apply a percentage down payment on a sale order", async () => {
    const store = await setupAndMountPosApp();

    await Utils.downPaymentSaleOrder("S00001", "+20", { percentage: true });

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].product_id.id).toBe(store.config.down_payment_product_id.id);
    // 20% of the 815 (500 + 150 + 165) of the sale order lines
    expect(order.lines[0].price_unit).toBe(163);
    expect(order.lines[0].sale_order_origin_id.id).toBe(1);
    expect(Utils.hasOrderline({ productName: "Down Payment (POS)", quantity: "1" })).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    expect(".payment-screen").toHaveCount(1);
});

test("a fixed down payment applies the typed amount", async () => {
    const store = await setupAndMountPosApp();

    await Utils.downPaymentSaleOrder("S00001", "+20");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].product_id.id).toBe(store.config.down_payment_product_id.id);
    expect(order.lines[0].price_unit).toBe(20);
});

test("PoSSaleOrderWithDownpayment: an invoiced down payment is deducted when settling", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00010");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(2);
    expect(order.lines[1].product_id.id).toBe(store.config.down_payment_product_id.id);
    expect(order.lines[1].qty).toBe(-1);
    expect(order.lines[1].price_unit).toBe(20);
    expect(order.priceIncl).toBe(980);
    expect(Utils.hasOrderline({ productName: "Down Payment (POS)" })).toBe(true);
});

test("test_pos_settle_so_with_downpayment: every down payment of the order is deducted", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00011");

    const order = store.getOrder();
    // the product line and the two down payments (invoiced and paid online)
    expect(order.lines).toHaveLength(3);
    expect(order.priceIncl).toBe(755);
});

test("test_down_payment_displayed: a down payment applied in the PoS is shown on the settled order", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00014");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(2);
    expect(order.lines[1].product_id.id).toBe(store.config.down_payment_product_id.id);
    expect(order.lines[1].qty).toBe(-1);
    expect(order.lines[1].prices.total_included).toBe(-1.15);
    expect(Utils.hasOrderline({ productName: "Down Payment (POS)", price: "-1.15" })).toBe(true);
});

test("PosSettleOrderNotGroupable: a non groupable line is split and keeps its discount", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00012");

    const order = store.getOrder();
    // 3.5 units of a product sold in kg are split in 4 lines
    expect(order.lines).toHaveLength(4);
    expect(order.lines.map((line) => line.qty)).toEqual([1, 1, 1, 0.5]);
    expect(order.lines[3].discount).toBe(10);
    // 3.5 * 8 * 1.15 * 90%
    expect(store.currency.round(order.priceIncl)).toBe(28.98);
    expect(Utils.getOrderTotal()).toInclude("28.98");
    expect(
        Utils.hasOrderline({ productName: "Pomme de Terre", quantity: "0.5", price: "4.14" })
    ).toBe(true);
});

test("PosSettleOrderWithNote: the notes of the sale order are merged in the customer note", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00013");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].customer_note).toBe("Customer note 2--Customer note 3");
    expect(Utils.hasOrderline({ customerNote: "Customer note 2--Customer note 3" })).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await waitFor(".feedback-screen");

    // the note is kept on the paid order (its rendering on the receipt is
    // covered by the point_of_sale receipt tests)
    expect(order.state).toBe("paid");
    expect(order.lines[0].customer_note).toBe("Customer note 2--Customer note 3");
});

test("PoSDownPaymentLinesPerTax: a down payment line is created per tax of the sale order", async () => {
    const store = await setupAndMountPosApp();

    await Utils.downPaymentSaleOrder("S00016", "+20", { percentage: true });

    const order = store.getOrder();
    // one line per tax: 10% excluded, 5% included and no tax
    expect(order.lines).toHaveLength(3);
    expect(order.lines.map((line) => line.tax_ids.map((tax) => tax.id))).toEqual([[], [20], [21]]);
    // 20% of the 15, 11 and 5 tax included totals of the sale order lines
    expect(order.lines.map((line) => line.prices.total_included)).toEqual([3, 2.2, 1]);
    expect(order.lines.every((line) => line.product_id.id === 105)).toBe(true);
    expect(Utils.hasOrderline({ productName: "Down Payment (POS)", price: "2.20" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Down Payment (POS)", price: "1.00" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Down Payment (POS)", price: "3.00" })).toBe(true);
});

test("test_settle_order_with_multiple_uom: a sale order mixing units of measure is settled", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00017");

    const order = store.getOrder();

    expect(order.lines).toHaveLength(3);
    expect(order.lines.map((line) => line.product_id.uom_id.id)).toEqual([1, 15, 15]);
    expect(order.lines.map((line) => line.qty)).toEqual([2, 1, 1]);
    expect(order.priceIncl).toBe(36);
});

test("test_settle_so_archived_attribute: an archived attribute line does not open the configurator", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00018");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].attribute_value_ids).toHaveLength(0);
    expect(".modal").toHaveCount(0);
    expect(Utils.hasOrderline({ productName: "Archived Attr Product", quantity: "1" })).toBe(true);
});

test("test_settle_so_custom_attribute_value: the custom attribute value is shown on the settled line", async () => {
    const store = await setupAndMountPosApp();

    await Utils.settleSaleOrder("S00015");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].custom_attribute_value_ids[0].custom_value).toBe("Value");
    expect(Utils.hasOrderline({ attributeLine: "Sprinkles, Customization: Yes: Value" })).toBe(
        true
    );
});

test("test_pos_settle_pre_paid_so: Settle fully Prepaid sale order", async () => {
    await setupAndMountPosApp();
    await Utils.settlePaidSaleOrder("S00019");
    expect(Utils.hasOrderline({ productName: "TEST", quantity: "1" })).toBe(true);
    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    const paymentLines = queryAll(".paymentline");
    expect(paymentLines).toHaveLength(1);
    expect(paymentLines[0].querySelector(".payment-name")).toHaveText(
        "Online Payment: PBNK1/2026/00001"
    );
    expect(paymentLines[0].querySelector(".payment-amount")).toHaveText("$101.00");
    expect(paymentLines[0].querySelector(".payment-name")).toHaveText(
        "Online Payment: PBNK1/2026/00001"
    );
    expect(paymentLines[0].querySelector(".delete-button")).toBeEmpty();
    await Utils.clickValidatePayment();

    await Utils.clickNextOrder();
    await waitFor(".product-screen");
});
