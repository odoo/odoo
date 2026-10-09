import { expect, test } from "@odoo/hoot";
import { createPaymentLine, getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentAdyen } from "@pos_adyen/app/utils/payment/payment_adyen";

definePosModels();

test("a successful response stores the card brand, which allows adjusting the payment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const pm = store.models["pos.payment.method"].get(2);
    const line = createPaymentLine(store, order, pm);
    const iface = new PaymentAdyen(store, pm);

    iface.handleSuccessResponse(
        line,
        { POIData: { POITransactionID: { TransactionID: "adyen-tx" } } },
        new URLSearchParams("cardType=visa&cardHolderName=John")
    );
    expect(line.card_brand).toBe("visa");
    expect(line.card_type).toBeEmpty();
    expect(iface.canBeAdjusted(line.uuid)).toBe(true);
});
