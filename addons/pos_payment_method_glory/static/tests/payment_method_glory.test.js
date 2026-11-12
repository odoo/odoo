import { describe, expect, test } from "@odoo/hoot";
import { defineModels, models, runTestScope } from "../../../web/static/tests/web_test_helpers";
import { defineBusModels } from "../../../bus/static/tests/bus_test_helpers";
import { PaymentMethodGlory } from "@pos_payment_method_glory/payment_method_glory";

describe.current.tags("headless");

class PosElectronicPayment extends models.ServerModel {
    _name = "pos.electronic.payment";

    start_payment() {
        return {
            transaction_id: "test_stripe_transaction",
            status: "pending",
            terminal_serial_number: "TEST",
            client_secret: "SECRET",
        };
    }

    get_transaction_status(id, transaction_id) {
        if (transaction_id === "resumed_payment") {
            return {
                transaction_id,
                status: "pending",
                stripe_status: "requires_payment_method",
                terminal_serial_number: "TEST",
                client_secret: "SECRET",
            };
        }
        return { transaction_id, status: "paid", card_type: "Visa" };
    }
}

defineModels([PosElectronicPayment]);
defineBusModels();

test("normal payment flow makes expected SDK calls", async () => {
    const paymentMethod = await runTestScope(() => new PaymentMethodGlory(1));
    let paymentResult = null;

    const response = await paymentMethod.startPayment(
        5.0,
        1,
        {},
        (response) => (paymentResult = response)
    );

    expect(response).toMatchObject({
        transaction_id: "test_stripe_transaction",
        status: "pending",
        terminal_serial_number: "TEST",
        client_secret: "SECRET",
    });

    expect(paymentResult).toEqual({
        status: "paid",
        card_type: "Visa",
        transaction_id: "test_stripe_transaction",
    });
});
