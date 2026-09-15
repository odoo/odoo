import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

test("set the default customer and check the invoice button by default", async () => {
    const store = await setupPosEnv();

    const twd = store.models["res.currency"].create({
        name: "TWD",
        symbol: "NT$",
        position: "before",
        rounding: 0.01,
        rate: 1.0,
        decimal_places: 2,
    });

    const countryId = store.models["res.country"].create({
        name: "Taiwan",
        code: "TW",
    });

    const companyId = store.models["res.company"].create({
        name: "Test Company",
        country_id: countryId,
        account_fiscal_country_id: countryId,
        currency_id: twd,
        l10n_tw_edi_ecpay_staging_mode: true,
        l10n_tw_edi_ecpay_merchant_id: "1234",
        l10n_tw_edi_ecpay_hashkey: "aaBBccDDeeFFggHH",
        l10n_tw_edi_ecpay_hashIV: "bbCCDDeeFFggHHaa",
        phone: "+886 123 456 781",
    });

    const walkInCustomerRecord = store.models["res.partner"].create({
        name: "Walk-in Customer",
        company_type: "individual",
        is_company: false,
    });

    const config = store.models["pos.config"].getFirst();
    config.update({
        is_ecpay_enabled: true,
        company_id: companyId,
        currency_id: twd,
    });

    config._tw_walk_in_customer = walkInCustomerRecord;
    config._tw_walk_in_customer.commercial_partner_id = walkInCustomerRecord;

    const order = store.addNewOrder();

    // The default customer should be the walk-in customer
    expect(order.partner_id.name).toBe("Walk-in Customer");
    await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    // The invoice button should be toggled in PaymentScreen if the customer is set
    expect(order.to_invoice).toBe(true);
});
