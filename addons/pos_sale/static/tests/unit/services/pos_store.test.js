import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { click, waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("onClickSaleOrder", () => {
    test("no selection → abort", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        const promiseResult = store.onClickSaleOrder(1);
        const button =
            ".modal-header:has(.modal-title:contains('What do you want to do?')) button[aria-label='Close']";
        await waitFor(button);
        await click(button);

        await promiseResult;

        const currentOrder = store.getOrder();
        expect(currentOrder.id).toBe(order.id);
        expect(currentOrder.lines.length).toBe(2);

        expect(currentOrder.lines[0].product_id.id).toBe(5);
        expect(currentOrder.lines[0].qty).toBe(3);

        expect(currentOrder.lines[1].product_id.id).toBe(6);
        expect(currentOrder.lines[1].qty).toBe(2);
    });

    test("PosSettleOrder: settle → calls settleSO", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        const promiseResult = store.onClickSaleOrder(1);
        const button = ".modal-body button:contains('Settle the order')";
        await waitFor(button);
        await click(button);
        await promiseResult;

        const currentOrder = store.getOrder();

        expect(currentOrder.id).toBe(order.id);
        expect(currentOrder.lines.length).toBe(4);

        expect(currentOrder.lines[0].product_id.id).toBe(5);
        expect(currentOrder.lines[0].qty).toBe(3);
        expect(currentOrder.lines[0].price_unit).toBe(3);
        expect(currentOrder.lines[0].prices.total_excluded).toBe(9);

        expect(currentOrder.lines[1].product_id.id).toBe(6);
        expect(currentOrder.lines[1].qty).toBe(2);
        expect(currentOrder.lines[1].price_unit).toBe(3);
        expect(currentOrder.lines[1].prices.total_excluded).toBe(6);

        expect(currentOrder.lines[2].product_id.id).toBe(5);
        expect(currentOrder.lines[2].qty).toBe(5);
        expect(currentOrder.lines[2].price_unit).toBe(100);
        expect(currentOrder.lines[2].prices.total_excluded).toBe(500);

        expect(currentOrder.lines[3].product_id.id).toBe(6);
        expect(currentOrder.lines[3].qty).toBe(3);
        expect(currentOrder.lines[3].price_unit).toBe(50);
        expect(currentOrder.lines[3].prices.total_excluded).toBe(150);
    });

    test("PosSettleCustomPrice: settle keeps custom sale order line price when partner changes", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const saleOrder = await store._getSaleOrder(1);
        const product = store.models["product.product"].get(5);
        const productTemplate = store.models["product.template"].get(5);
        product.lst_price = 150;
        productTemplate.list_price = 150;

        await store.settleSO(saleOrder, saleOrder.fiscal_position_id);

        const settledLine = order.lines.find((line) => line.sale_order_line_id?.id === 1);
        expect(settledLine.price_unit).toBe(100);

        store.setPartnerToCurrentOrder(store.models["res.partner"].get(4));

        expect(settledLine.price_unit).toBe(100);
    });

    test("PoSSaleOrderWithDownpayment / PoSApplyDownpayment: dpPercentage → calls downPaymentSO", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        const promiseResult = store.onClickSaleOrder(1);
        const buttonDownPaymentPercentage =
            ".modal-body button:contains('Apply a down payment (percentage)')";
        await waitFor(buttonDownPaymentPercentage);
        await click(buttonDownPaymentPercentage);
        await waitFor(".modal-title:contains('Down Payment')");
        await click(".modal-body .numpad .numpad-button[value='+50']");
        await new Promise((resolve) => setTimeout(resolve, 50));
        await click(".modal-footer .btn:contains('Apply')");
        await promiseResult;

        const currentOrder = store.getOrder();
        expect(currentOrder.id).toBe(order.id);
        expect(currentOrder.lines.length).toBe(3);

        expect(currentOrder.lines[0].product_id.id).toBe(5);
        expect(currentOrder.lines[0].qty).toBe(3);
        expect(currentOrder.lines[0].price_unit).toBe(3);
        expect(currentOrder.lines[0].prices.total_excluded).toBe(9);

        expect(currentOrder.lines[1].product_id.id).toBe(6);
        expect(currentOrder.lines[1].qty).toBe(2);
        expect(currentOrder.lines[1].price_unit).toBe(3);
        expect(currentOrder.lines[1].prices.total_excluded).toBe(6);

        expect(currentOrder.lines[2].product_id.id).toBe(105);
        expect(currentOrder.lines[2].qty).toBe(1);
        expect(currentOrder.lines[2].price_unit).toBe(325);
        expect(currentOrder.lines[2].prices.total_excluded).toBe(325);

        const comp = await mountWithCleanup(Orderline, {
            props: { line: currentOrder.lines[2] },
        });

        const saleOrderInfo = ".orderline .info-list .sale-order-info";
        const cell = (tr, td) => `${saleOrderInfo} tr:nth-child(${tr}) td:nth-child(${td})`;

        expect(comp.line).toEqual(currentOrder.lines[2]);
        expect(`${saleOrderInfo} tr`).toHaveCount(4);

        expect(cell(1, 1)).toHaveText("5x");
        expect(cell(1, 2)).toHaveText("TEST");
        expect(cell(1, 4)).toHaveText(`$ 500.00 (tax incl.)`);

        expect(cell(2, 1)).toHaveText("3x");
        expect(cell(2, 2)).toHaveText("TEST 2");
        expect(cell(2, 4)).toHaveText(`$ 150.00 (tax incl.)`);
    });

    test("PoSSaleOrderWithDownpayment / PoSApplyDownpayment: dpAmount → calls downPaymentSO", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        const promiseResult = store.onClickSaleOrder(1);
        const buttonDownPaymentPercentage =
            ".modal-body button:contains('Apply a down payment (fixed amount)')";
        await waitFor(buttonDownPaymentPercentage);
        await click(buttonDownPaymentPercentage);
        await waitFor(".modal-title:contains('Down Payment')");
        await click(".modal-body .numpad .numpad-button[value='+50']");
        await new Promise((resolve) => setTimeout(resolve, 50));
        await click(".modal-footer .btn:contains('Apply')");
        await promiseResult;

        const currentOrder = store.getOrder();
        expect(currentOrder.id).toBe(order.id);
        expect(currentOrder.lines.length).toBe(3);

        expect(currentOrder.lines[0].product_id.id).toBe(5);
        expect(currentOrder.lines[0].qty).toBe(3);
        expect(currentOrder.lines[0].price_unit).toBe(3);
        expect(currentOrder.lines[0].prices.total_excluded).toBe(9);

        expect(currentOrder.lines[1].product_id.id).toBe(6);
        expect(currentOrder.lines[1].qty).toBe(2);
        expect(currentOrder.lines[1].price_unit).toBe(3);
        expect(currentOrder.lines[1].prices.total_excluded).toBe(6);

        expect(currentOrder.lines[2].product_id.id).toBe(105);
        expect(currentOrder.lines[2].qty).toBe(1);
        expect(currentOrder.lines[2].price_unit).toBe(50);
        expect(currentOrder.lines[2].prices.total_excluded).toBe(50);

        const comp = await mountWithCleanup(Orderline, {
            props: { line: currentOrder.lines[2] },
        });

        const saleOrderInfo = ".orderline .info-list .sale-order-info";
        const cell = (tr, td) => `${saleOrderInfo} tr:nth-child(${tr}) td:nth-child(${td})`;

        expect(comp.line).toEqual(currentOrder.lines[2]);
        expect(`${saleOrderInfo} tr`).toHaveCount(4);

        expect(cell(1, 1)).toHaveText("5x");
        expect(cell(1, 2)).toHaveText("TEST");
        expect(cell(1, 4)).toHaveText(`$ 500.00 (tax incl.)`);

        expect(cell(2, 1)).toHaveText("3x");
        expect(cell(2, 2)).toHaveText("TEST 2");
        expect(cell(2, 4)).toHaveText(`$ 150.00 (tax incl.)`);
    });

    test("sale order: ignore lines with zero quantity", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        const promiseResult = store.onClickSaleOrder(2);
        const button = ".modal-body button:contains('Settle the order')";
        await waitFor(button);
        await click(button);
        await promiseResult;

        expect(order.lines.length).toBe(3);
        expect(order.lines[2].product_id.id).toBe(5);
        expect(order.lines[2].qty).toBe(5);
        expect(order.lines[2].price_unit).toBe(100);
        expect(order.lines[2].prices.total_excluded).toBe(500);
    });

    test("PosSettleOrderIncompatiblePartner: setting warned partners shows the corresponding alerts", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const warnedPartnerA = store.models["res.partner"].get(4);
        const warnedPartnerB = store.models["res.partner"].get(3);
        warnedPartnerA.name = "A Test Customer 1";
        warnedPartnerA.sale_warn_msg = "Highly infectious disease";
        warnedPartnerB.name = "A Test Customer 2";
        warnedPartnerB.sale_warn_msg = "Cannot afford our services";

        const dialogs = [];
        store.dialog.add = (component, props) => dialogs.push({ component, props });

        store.setPartnerToCurrentOrder(warnedPartnerB);
        store.setPartnerToCurrentOrder(warnedPartnerA);

        expect(order.getPartner()).toBe(warnedPartnerA);
        expect(dialogs).toHaveLength(2);
        expect(dialogs[0].component).toBe(AlertDialog);
        expect(dialogs[0].props.title).toBe("Warning for A Test Customer 2");
        expect(dialogs[0].props.body).toBe("Cannot afford our services");
        expect(dialogs[1].component).toBe(AlertDialog);
        expect(dialogs[1].props.title).toBe("Warning for A Test Customer 1");
        expect(dialogs[1].props.body).toBe("Highly infectious disease");
    });
});

describe("getConvertedQuantityFromSaleOrderline", () => {
    test("service product, state != sent/draft → qty_to_invoice", async () => {
        const store = await setupPosEnv();
        const product = store.models["product.product"].getFirst();
        product.type = "service";

        const saleOrderLine = {
            qty_to_invoice: 2,
            product_id: product,
            order_id: { state: "sale" },
        };
        const qty = await store.getConvertedQuantityFromSaleOrderline(saleOrderLine, saleOrderLine);
        expect(qty).toBe(2);
    });

    test("non-service product → qty = uom_qty - max(delivered, invoiced)", async () => {
        const store = await setupPosEnv();
        const product = store.models["product.product"].getFirst();
        product.type = "consu";

        const saleOrderLine = {
            product_uom_qty: 8,
            qty_delivered: 1,
            qty_invoiced: 2,
            qty_to_invoice: 6,
            product_id: product,
            order_id: { state: "sale" },
        };

        const qty = await store.getConvertedQuantityFromSaleOrderline(saleOrderLine, saleOrderLine);
        expect(qty).toBe(6);
    });
});

test("PosSettleOrderIncompatiblePartner: incompatible partner creates a new POS order", async () => {
    const store = await setupPosEnv();
    const initialOrder = store.addNewOrder();
    const saleOrder1 = await store._getSaleOrder(1);
    await store.settleSO(saleOrder1, saleOrder1.fiscal_position_id);

    const saleOrder2 = await store._getSaleOrder(11);

    store.dialog.add = (component, props) => {
        if (props.list && props.getPayload) {
            props.getPayload("settle");
            return;
        }
        if (props.confirm) {
            props.confirm();
        }
    };

    await store._processSaleOrder(saleOrder2);

    expect(store.getOrder().id).not.toBe(initialOrder.id);
    expect(store.getOrder().getPartner().id).toBe(4);
});

test("PosSettleOrder: sale order line notes are merged into customer note", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const saleOrder = await store._getSaleOrder(4);

    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);

    expect(store.getOrder().lines[0].customer_note).toBe("Customer note 2--Customer note 3");
});

test("test_settle_so_with_non_pos_groupable_uom: settling a non-groupable UoM line preserves converted quantity", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const saleOrder = await store._getSaleOrder(5);
    const product = store.models["product.product"].get(5);
    product.uom_id.is_pos_groupable = false;

    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);

    expect(store.getOrder().lines).toHaveLength(1);
    expect(store.getOrder().lines[0].qty).toBe(0.5);
    expect(store.getOrder().lines[0].price_unit).toBe(10);
});

test("test_quantity_updated_settle: re-settling uses updated remaining quantity", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const saleOrder = await store._getSaleOrder(10);
    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);
    expect(store.getOrder().lines[0].qty).toBe(5);

    const nextOrder = store.addNewOrder();
    const originalCall = store.data.call.bind(store.data);
    store.data.call = async (model, method, args) => {
        const result = await originalCall(model, method, args);
        if (model === "sale.order.line" && method === "read_converted") {
            result[0].qty_delivered = 2;
        }
        return result;
    };
    const saleOrderLatest = await store._getSaleOrder(10);
    await store.settleSO(saleOrderLatest, saleOrderLatest.fiscal_position_id);
    expect(nextOrder.lines[0].qty).toBe(3);
    expect(nextOrder.lines[0].price_unit).toBe(11.5);
});

test("test_settle_changed_price_with_lots: settle keeps custom line prices, including lot-tracked products", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const saleOrder = await store._getSaleOrder(8);
    const product = store.models["product.product"].get(5);
    product.tracking = "lot";
    product.lst_price = 100;

    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);

    expect(store.getOrder().priceIncl).toBe(180);
    expect(store.getOrder().lines.some((line) => line.price_unit === 100)).toBe(false);
});

test("test_settle_groupable_lot_total_amount: groupable lot-tracked line keeps expected total", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const saleOrder = await store._getSaleOrder(9);
    const product = store.models["product.product"].get(5);
    product.tracking = "lot";
    product.uom_id.is_pos_groupable = true;
    store.dialog.add = (component, props) => {
        props?.confirm();
    };

    await store.settleSO(saleOrder, saleOrder.fiscal_position_id);

    expect(store.getOrder().priceIncl).toBe(12);
});
