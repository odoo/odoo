import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { onRpc } from "@web/../tests/web_test_helpers";

definePosModels();

test("ECPay error of an invoiced order is kept on the order", async () => {
    const store = await setupPosEnv();
    onRpc("pos.order", "l10n_tw_edi_get_uniform_invoice", () => ({
        ecpay_error: "Invoice number: INV/2026/00001 Error: ECPay is down",
    }));
    const order = store.addNewOrder();
    order.is_singly_invoiced = true;

    await store._getUniformInvoiceData(order);

    // The error must be stored on the order (it prevents printing an empty e-invoice)
    // instead of being ignored and overwriting the e-invoice data with undefined values.
    expect(order.ecpay_error).toBe("Invoice number: INV/2026/00001 Error: ECPay is down");
});
