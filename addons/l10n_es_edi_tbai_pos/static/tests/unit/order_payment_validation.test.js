import { expect, test } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("finalizeValidation", async () => {
    const url = "https://tbai-receipt-url/1234";
    onRpc("pos.order", "get_l10n_es_pos_tbai_qrurl", () => url);
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });
    await validation.finalizeValidation();
    const receipt = store.ticketPrinter.getOrderReceiptData(order);
    expect(receipt.image.l10n_es_pos_tbai_qrsrc).toBe(generateQRCodeDataUrl(url));
});
