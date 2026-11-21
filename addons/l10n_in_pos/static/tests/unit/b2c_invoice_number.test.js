import { expect, test } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

const { DateTime } = luxon;

definePosModels();

test("invoices and refunds are numbered from separate device counters", async () => {
    const store = await setupPosEnv();
    store.company.country_id.code = "IN";
    store.config.l10n_in_b2c_invoice_prefix = "P";
    const bankPM = store.models["pos.payment.method"].get(2);

    const getOrderB2CInvoiceNumber = async (vals = {}) => {
        const order = await getFilledOrder(store, vals);
        order.addPaymentline(bankPM);
        await store.validateOrder({ order });
        return order.l10n_in_b2c_invoice_number;
    };
    // Config 1 on device 1
    const year2Digits = DateTime.now().year.toString().slice(-2);
    expect(await getOrderB2CInvoiceNumber()).toBe(`P${year2Digits}/0101/0000001`);
    expect(await getOrderB2CInvoiceNumber({ is_refund: true })).toBe(
        `R${year2Digits}/0101/0000001`
    );
    expect(await getOrderB2CInvoiceNumber()).toBe(`P${year2Digits}/0101/0000002`);

    // The number follows the device identifier
    store.device.save({ device_identifier: 2 });
    expect(await getOrderB2CInvoiceNumber()).toBe(`P${year2Digits}/0102/0000003`);
});
