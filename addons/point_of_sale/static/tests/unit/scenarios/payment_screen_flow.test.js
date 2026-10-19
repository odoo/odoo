import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor, advanceTime } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { localization } from "@web/core/l10n/localization";
import {
    setupAndMountPosApp,
    enableCashRounding,
    addTestTerminals,
} from "@point_of_sale/../tests/unit/utils";
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
    patch(localization, { decimalPoint: ",", thousandsSep: "." });

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

test("Check flow with multi currency payment lines", async () => {
    await setupAndMountPosApp();
    await Utils.clickDisplayedProduct("Steel desk");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickCurrencyWisePaymentMethod("Cash", "USD", "875.00");
    expect(await Utils.selectedPaymentLineHasAmount("$875.00")).toBe(true);
    await Utils.paymentScreenAmountTotal("875.00");
    await Utils.deletePaymentline({ name: "Cash", amount: "875.00" });
    await Utils.clickCurrencyWisePaymentMethod("Cash", "EUR", "761.25");
    expect(await Utils.selectedPaymentLineHasAmount("761.25€")).toBe(true);
    await Utils.paymentScreenAmountTotal("761.25");
    await Utils.sendBufferKeys("5");
    await Utils.paymentScreenRemainingTotal("756.25");
    expect(await Utils.selectedPaymentLineHasAmount("5.00€")).toBe(true);
    await Utils.deletePaymentline({ name: "Cash", amount: "5.00" });
    await Utils.clickCurrencyWisePaymentMethod("Cash", "EUR", "761.25");
    await Utils.clickValidatePayment();
    await waitFor(".feedback-screen");
});

test("AutofillCashCount: cash count autofill with comma decimal separator", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    patch(localization, { decimalPoint: ",", thousandsSep: "." });

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

test("Default payment method: selected once, then used directly", async () => {
    const store = await setupAndMountPosApp({
        module_pos_restaurant: false,
        available_preset_ids: [],
        fast_payment_method_ids: [],
    });
    const [terminal1, terminal2] = addTestTerminals(store);

    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    expect(".paymentmethod:contains('Test Terminal')").toHaveCount(0);

    // The provider button asks for the default, then adds the payment line
    await Utils.clickPaymentMethod("Test Provider");
    await Utils.selectDefaultPaymentMethodInPopup("Test Terminal 2");
    await animationFrame();
    expect(store.paymentMethods.getDefault("test_terminal")).toBe(terminal2);
    expect(Utils.selectedPaymentline().name).toBe("Test Terminal 2");
    expect(".paymentmethod:contains('Test Provider')").toHaveCount(0);
    expect(".paymentmethod:contains('Test Terminal 1')").toHaveCount(0);

    // The default can be changed from the burger menu
    await Utils.clickPaymentMethod("Test Terminal 1", true);
    expect(store.paymentMethods.getDefault("test_terminal")).toBe(terminal1);
    expect(Utils.selectedPaymentline().name).toBe("Test Terminal 1");
    expect(".paymentmethod:contains('Test Terminal 2')").toHaveCount(0);
});
