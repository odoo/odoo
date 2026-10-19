import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class AccountMove extends models.Model {
    _name = "account.move";

    invoice_payments_widget = fields.Json();

    // This mock method intercepts the RPC call triggered by the widget's Unreconcile button.
    js_remove_outstanding_partial(moveId, partialId) {
        expect([moveId, partialId]).toEqual([2, 3]);
        expect.step("unreconcile");
    }

    _records = [
        {
            id: 1,
            invoice_payments_widget: {
                content: [
                    {
                        amount: 100,
                        amount_company_currency: "$100.00",
                        company_name: "Other Company",
                        currency_id: 1,
                        date: "2026-09-16",
                        journal_name: "Bank",
                        move_id: 2,
                        partial_id: 3,
                        payment_method_name: "Manual",
                        ref: "BNK1/2026/00001",
                    },
                ],
                exchange_info: {},
                outstanding: false,
                title: "Less Payment",
            },
        },
        {
            // What the server sends for a payment in the company of the invoice,
            // without a foreign currency and without a payment method.
            id: 2,
            invoice_payments_widget: {
                content: [
                    {
                        amount: 100,
                        amount_company_currency: "$100.00",
                        amount_foreign_currency: null,
                        company_name: false,
                        currency_id: 1,
                        date: "2026-09-16",
                        journal_name: "Miscellaneous Operations",
                        move_id: 4,
                        partial_id: 5,
                        payment_method_name: false,
                        ref: "MISC/2026/09/0001",
                    },
                ],
                exchange_info: {},
                outstanding: false,
                title: "Less Payment",
            },
        },
    ];

    _views = {
        form: `
            <form>
                <field name="invoice_payments_widget" widget="payment"/>
            </form>
        `,
    };
}

defineModels([AccountMove]);
defineMailModels();

test("payment popover can unreconcile a payment", async () => {
    await mountView({
        type: "form",
        resModel: "account.move",
        resId: 1,
    });

    await contains(".js_payment_info").click();
    expect(".account_payment_popover").toHaveText(/BNK1\/2026\/00001/);

    await contains(".js_unreconcile_payment").click();
    expect.verifySteps(["unreconcile"]);
});

test("payment popover opens without a company, a foreign currency or a payment method", async () => {
    await mountView({
        type: "form",
        resModel: "account.move",
        resId: 2,
    });

    await contains(".js_payment_info").click();
    expect(".account_payment_popover").toHaveText(/MISC\/2026\/09\/0001/);
});
