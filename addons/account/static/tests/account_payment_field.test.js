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
