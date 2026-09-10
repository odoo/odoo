import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

definePosModels();

const setupRefundOrder = async (originalPaidWithSumup) => {
    const store = await setupPosEnv();
    const sumupPm = store.models["pos.payment.method"].find(
        (pm) => pm.payment_provider === "sumup"
    );
    const originalPaymentMethod = originalPaidWithSumup
        ? sumupPm
        : store.models["pos.payment.method"].get(2);

    const originalOrder = await getFilledOrder(store);

    const refundOrder = store.addNewOrder({ is_refund: true });
    await store.addLineToOrder(
        {
            product_tmpl_id: store.models["product.template"].get(5),
            qty: -1,
            refunded_orderline_id: originalOrder.lines[0],
        },
        refundOrder,
        {},
        false
    );
    const amountDue = Math.abs(refundOrder.remainingDue);

    store.models["pos.payment"].create({
        amount: amountDue,
        payment_method_id: originalPaymentMethod.id,
        pos_order_id: originalOrder.id,
        transaction_id: "orig_ctid",
    });

    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: refundOrder.uuid },
    });
    return { comp, refundOrder, sumupPm };
};

describe("addNewPaymentLine: sumup refund matching", () => {
    test("copies the transaction id from a matched original SumUp payment", async () => {
        const { comp, refundOrder, sumupPm } = await setupRefundOrder(true);

        await comp.addNewPaymentLine(sumupPm);

        expect(refundOrder.payment_ids).toHaveLength(1);
        expect(refundOrder.payment_ids[0].transaction_id).toBe("orig_ctid");
    });

    test("adds the line without a transaction id when the original order wasn't paid with SumUp", async () => {
        const { comp, refundOrder, sumupPm } = await setupRefundOrder(false);

        await comp.addNewPaymentLine(sumupPm);

        expect(refundOrder.payment_ids).toHaveLength(1);
        expect(Boolean(refundOrder.payment_ids[0].transaction_id)).toBe(false);
    });
});
