import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PosSession } from "@point_of_sale/../tests/unit/data/pos_session.data";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

test("ECPay error of an invoiced order is kept on the order", async () => {
    // The PoS loads account.move (pos.session._load_pos_data_models), the test data does not.
    patchWithCleanup(PosSession.prototype, {
        _load_pos_data_models() {
            return [...super._load_pos_data_models(), "account.move"];
        },
    });
    const store = await setupPosEnv();
    onRpc("pos.order", "l10n_tw_edi_get_uniform_invoice", () => ({
        ecpay_error: "Invoice number: INV/2026/00001 Error: ECPay is down",
    }));
    const order = store.addNewOrder();
    order.account_move = store.models["account.move"].create({ id: 4242 });

    await store._getUniformInvoiceData(order);

    // The error must be stored on the order (it prevents printing an empty e-invoice)
    // instead of being ignored and overwriting the e-invoice data with undefined values.
    expect(order.ecpay_error).toBe("Invoice number: INV/2026/00001 Error: ECPay is down");
});
