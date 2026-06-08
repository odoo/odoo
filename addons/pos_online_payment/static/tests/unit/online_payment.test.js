import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

definePosModels();

test("OnlinePaymentErrorsTour: rejects negative remaining online payment line", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const onlinePaymentMethod = store.models["pos.payment.method"].get(2);
    onlinePaymentMethod.is_online_payment = true;

    createPaymentLine(store, order, onlinePaymentMethod, {
        amount: -1,
    });

    const dialogs = [];
    store.dialog.add = (component, props) => dialogs.push(props);

    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: order.uuid,
    });

    expect(validation.checkRemainingOnlinePaymentLines(1)).toBe(false);
    expect(dialogs).toHaveLength(1);
    expect(dialogs[0].title).toBe("Invalid online payment");
});

test("OnlinePaymentErrorsTour: rejects mismatch between unpaid amount and remaining online payments", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const onlinePaymentMethod = store.models["pos.payment.method"].get(2);
    onlinePaymentMethod.is_online_payment = true;

    createPaymentLine(store, order, onlinePaymentMethod, {
        amount: 10,
    });

    const dialogs = [];
    store.dialog.add = (component, props) => dialogs.push(props);

    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: order.uuid,
    });

    expect(validation.checkRemainingOnlinePaymentLines(8)).toBe(false);
    expect(dialogs).toHaveLength(1);
    expect(dialogs[0].title).toBe("Invalid online payments");
});

test("test_payment_method_customer_required", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const onlinePaymentMethod = store.models["pos.payment.method"].get(2);
    const partner = store.models["res.partner"].get(3);
    onlinePaymentMethod.is_online_payment = true;
    onlinePaymentMethod._customer_required = true;
    partner.email = false;

    order.partner_id = partner;
    createPaymentLine(store, order, onlinePaymentMethod, {
        amount: order.remainingDue,
    });

    const dialogs = [];
    store.dialog.add = (component, props) => dialogs.push(props);

    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: order.uuid,
    });
    const isValid = await validation.isOrderValid(false);

    expect(isValid).toBe(false);
    expect(dialogs).toHaveLength(1);
    expect(dialogs[0].title).toBe("Payment provider requirement");
});

test("test_selected_customer_after_adding_payment_sync", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const onlinePaymentMethod = store.models["pos.payment.method"].get(2);
    const partner = store.models["res.partner"].get(3);
    onlinePaymentMethod.is_online_payment = true;

    order.partner_id = partner;
    const paymentLine = createPaymentLine(store, order, onlinePaymentMethod, {
        amount: order.remainingDue,
        payment_status: "waiting",
    });

    const onlinePaymentData = {
        id: order.id,
        online_payments: [
            {
                payment_method_id: onlinePaymentMethod.id,
                amount: paymentLine.getAmount(),
            },
        ],
    };

    const result = store.processOnlinePaymentsDataFromServer(order, onlinePaymentData);

    expect(order.partner_id).toBe(partner);
    expect(result.isPaid).toBe(false);
    expect(paymentLine.getPaymentStatus()).toBe("done");
});

test("OnlinePaymentErrorsTour: does not serialize unsynced online payments to ORM", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const cashPaymentMethod = store.models["pos.payment.method"].get(1);
    const onlinePaymentMethod = store.models["pos.payment.method"].get(2);
    onlinePaymentMethod.is_online_payment = true;
    cashPaymentMethod.is_online_payment = false;

    createPaymentLine(store, order, cashPaymentMethod, {
        amount: 5,
        isSynced: false,
    });
    createPaymentLine(store, order, onlinePaymentMethod, {
        amount: 7,
        isSynced: false,
    });

    const serialized = order.serializeForORM();

    expect(serialized.payment_ids).toHaveLength(1);
});
