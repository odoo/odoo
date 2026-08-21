import { expect, test } from "@odoo/hoot";
import { waitFor, waitUntil } from "@odoo/hoot-dom";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as OpUiUtils from "@pos_online_payment/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...OpUiUtils };

definePosModels();

test.tags("desktop");
test("OnlinePaymentErrorsTour: invalid online payment lines are refused and dropped", async () => {
    const store = await setupAndMountPosApp(Utils.ONLINE_PAYMENT_POS_CONFIG);
    Utils.addOnlinePaymentMethod(store);
    Utils.setFlatProductPrice(store, 4.8);

    await Utils.clickDisplayedProduct("TEST");
    await Utils.sendBufferKeys("1");
    await Utils.sendBufferKeys("0");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].qty).toBe(10);
    expect(order.totalDue).toBe(48);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    expect(".paymentlines-empty").toHaveCount(1);

    await Utils.clickPaymentMethod("Online payment");
    expect(Utils.getOnlinePaymentLines(order)[0].getAmount()).toBe(48);

    await Utils.enterPaymentlineAmount(47);
    expect(Utils.getOnlinePaymentLines(order)[0].getAmount()).toBe(47);
    expect(order.remainingDue).toBe(1);
    expect(Utils.isValidateHighlighted()).toBe(false);

    await Utils.clickPaymentMethod("Cash");
    await Utils.enterPaymentlineAmount(2);
    expect(order.getSelectedPaymentline().getAmount()).toBe(2);
    expect(order.remainingDue).toBe(0);
    expect(Utils.isValidateHighlighted()).toBe(true);

    await Utils.clickValidatePayment();
    await waitFor(".modal");
    expect(".modal-title").toHaveText("Invalid online payments");
    await Utils.confirmDialog();

    await waitUntil(() => Utils.getOnlinePaymentLines(order).length === 0);
    expect(order.remainingDue).toBe(46);
    expect(order.state).toBe("draft");

    await Utils.clickPaymentMethod("Online payment");
    await Utils.clickPaymentMethod("Online payment");
    expect(Utils.getOnlinePaymentLines(order).map((line) => line.getAmount())).toEqual([46, 0]);
    expect(order.remainingDue).toBe(0);
    expect(Utils.isValidateHighlighted()).toBe(true);

    await Utils.clickValidatePayment();
    await waitFor(".modal");
    expect(".modal-title").toHaveText("Invalid online payment");
    await Utils.confirmDialog();

    await waitUntil(() => Utils.getOnlinePaymentLines(order).length === 0);
    expect(order.remainingDue).toBe(46);

    await Utils.clickPaymentMethod("Online payment");
    await Utils.clickPaymentMethod("Online payment");
    await Utils.clickPaymentline("Online payment", "0.00");
    await Utils.deletePaymentline("Online payment", "0.00");
    expect(Utils.getOnlinePaymentLines(order).map((line) => line.getAmount())).toEqual([46]);

    await Utils.clickPaymentline("Cash", "2.00");
    await Utils.enterPaymentlineAmount(3);
    expect(order.getSelectedPaymentline().getAmount()).toBe(3);

    await Utils.clickPaymentMethod("Online payment");
    expect(Utils.getOnlinePaymentLines(order).map((line) => line.getAmount())).toEqual([46, -1]);
    expect(order.remainingDue).toBe(0);
    expect(Utils.isValidateHighlighted()).toBe(true);

    await Utils.clickValidatePayment();
    await waitFor(".modal");
    expect(".modal-title").toHaveText("Invalid online payment");
    await Utils.confirmDialog();

    await waitUntil(() => Utils.getOnlinePaymentLines(order).length === 0);
    expect(order.state).toBe("draft");
    expect(order.payment_ids.map((line) => line.payment_method_id.name)).toEqual(["Cash"]);
});

test("test_payment_method_customer_required: the provider needs a customer with an email", async () => {
    const store = await setupAndMountPosApp(Utils.ONLINE_PAYMENT_POS_CONFIG);
    Utils.addOnlinePaymentMethod(store, { customerRequired: true });
    Utils.setFlatProductPrice(store, 4.8);

    await Utils.clickDisplayedProduct("TEST");

    const order = store.getOrder();
    expect(order.totalDue).toBe(4.8);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Online payment");
    expect(Utils.getOnlinePaymentLines(order)[0].getAmount()).toBe(4.8);

    expect(order.isCustomerRequired).toBe(true);
    expect(Utils.isValidateHighlighted()).toBe(false);

    await Utils.selectCustomerOnPaymentScreen("Administrator");
    expect(order.partner_id.name).toBe("Administrator");
    expect(order.isCustomerRequired).toBe(false);
    expect(Utils.isValidateHighlighted()).toBe(true);

    await Utils.clickValidatePayment();
    await waitFor(".modal");
    expect(".modal-title").toHaveText("Payment provider requirement");
    await Utils.confirmDialog();

    expect(order.state).toBe("draft");
});
