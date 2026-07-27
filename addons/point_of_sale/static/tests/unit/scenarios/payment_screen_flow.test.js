import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor, advanceTime } from "@odoo/hoot-dom";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
import { setupAndMountPosApp, enableCashRounding } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("PaymentScreenRoundingUp: cash rounding up with refund", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 1.96;
    productTmpl.taxes_id = false;
    store.models["product.product"].get(5).lst_price = 1.96;

    enableCashRounding(store, "UP");
    await animationFrame();

    const order = store.getOrder();

    await Utils.clickDisplayedProduct("TEST");
    expect(order.lines).toHaveLength(1);
    expect(Utils.getOrderTotal().includes("1.96")).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    await Utils.clickPaymentMethod("Cash");
    expect(order.payment_ids[0].amount).toBe(2.0);

    await Utils.clickValidatePayment();

    await Utils.clickNextOrder();
    await waitFor(".product-screen");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");

    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");
    await animationFrame();
    await contains('.ticket-screen .order-row:contains("001")').click();
    await animationFrame();

    if (Utils.isMobile()) {
        await Utils.clickTicketReviewButton();
        Utils.sendBufferKeys("1");
        await animationFrame();
        await Utils.clickTicketAction("Refund");
    } else {
        await Utils.clickNumpad("1");
        await contains('.ticket-screen .pads button:contains("Refund")').click();
        await animationFrame();
    }

    await waitFor(".payment-screen");

    const refundOrder = store.getOrder();
    await Utils.clickPaymentMethod("Cash");
    expect(refundOrder.payment_ids[0].amount).toBe(-2.0);
});

test("PaymentScreenRoundingDown: cash rounding down with refund", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 1.98;
    productTmpl.taxes_id = false;
    store.models["product.product"].get(5).lst_price = 1.98;

    enableCashRounding(store, "DOWN");
    await animationFrame();

    const order = store.getOrder();
    await Utils.clickDisplayedProduct("TEST");
    expect(order.lines).toHaveLength(1);
    expect(Utils.getOrderTotal().includes("1.98")).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    await Utils.clickPaymentMethod("Cash");
    expect(order.payment_ids[0].amount).toBe(1.95);

    await Utils.clickValidatePayment();

    await Utils.clickNextOrder();
    await waitFor(".product-screen");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");

    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");
    await animationFrame();
    await contains('.ticket-screen .order-row:contains("001")').click();
    await animationFrame();

    if (Utils.isMobile()) {
        await Utils.clickTicketReviewButton();
        Utils.sendBufferKeys("1");
        await animationFrame();
        await Utils.clickTicketAction("Refund");
    } else {
        await Utils.clickNumpad("1");
        await contains('.ticket-screen .pads button:contains("Refund")').click();
        await animationFrame();
    }

    await waitFor(".payment-screen");

    const refundOrder = store.getOrder();
    await Utils.clickPaymentMethod("Cash");
    expect(refundOrder.payment_ids[0].amount).toBe(-1.95);
});

test("PaymentScreenTotalDueWithOverPayment: overpayment shows correct change", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 1.98;
    productTmpl.taxes_id = false;
    store.models["product.product"].get(5).lst_price = 1.98;

    enableCashRounding(store, "DOWN");
    await animationFrame();
    const order = store.getOrder();
    await Utils.clickDisplayedProduct("TEST");
    expect(order.lines).toHaveLength(1);
    expect(Utils.getOrderTotal().includes("1.98")).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    await Utils.clickPaymentMethod("Cash");
    await Utils.sendBufferKeys("5");

    expect(order.payment_ids[0].amount).toBe(5);
    expect(order.change).toBe(-3.05);
});

test("test_pos_large_amount_confirmation_dialog: large payment asks for confirmation", async () => {
    await setupAndMountPosApp({ payment_method_ids: [2] });

    await Utils.clickDisplayedProduct("TEST");

    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    await Utils.clickPaymentMethod("Card");
    await Utils.sendBufferKeys("1", "5", "0");

    await waitFor('.modal .modal-title:contains("Maximum Value reached")');
    await contains(".modal .modal-footer .btn-primary").click();
    await Utils.clickValidatePayment();
    await animationFrame();
});

test.tags("desktop");

test("test_add_money_button_with_different_decimal_separator: +50 button works with comma separator", async () => {
    await setupAndMountPosApp();
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    await Utils.clickPaymentMethod("Card");

    await contains('.numpad button:contains("+50")').click();
    await animationFrame();
    await advanceTime(350);
    expect(await Utils.selectedPaymentLineHasAmount("$165,00")).toBe(true);
});

test("PaymentScreenTour2: change without cash payment method shows error", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false, payment_method_ids: [2] });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 10;
    productTmpl.taxes_id = [];
    store.models["product.product"].get(5).lst_price = 10;

    const order = store.getOrder();
    await animationFrame();

    await Utils.clickDisplayedProduct("TEST");
    expect(order.lines).toHaveLength(1);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    await Utils.clickPaymentMethod("Card");
    await Utils.sendBufferKeys("9", "9");

    await waitFor(".modal");
    await Utils.confirmDialog();

    const remaining = document.querySelector(".payment-status-remaining");
    expect(remaining).toBe(null);
});

test("AutofillCashCount: cash count autofill with comma decimal separator", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 123456;
    productTmpl.taxes_id = [];
    store.models["product.product"].get(5).lst_price = 123456;

    const order = store.getOrder();

    await animationFrame();

    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Cash");

    expect(order.payment_ids[0].amount).toBe(123456);
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();
    await waitFor(".product-screen");

    await contains(
        ".pos-leftheader button:has([data-icon='menu']), .pos-topheader button:has([data-icon='menu'])"
    ).click();
    await animationFrame();
    await contains(".o_pos_burger_menu_buttons button:contains('Close Register')").click();
    await animationFrame();

    await waitFor(".close-pos-popup");
    expect(document.querySelector(".close-pos-popup .cash-difference").textContent).toInclude("0");
    expect(document.querySelector(".close-pos-popup .cash-input input").value).toBe("123.456,00");
});
