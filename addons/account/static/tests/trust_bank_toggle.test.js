import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    makeServerError,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class ResPartnerBank extends models.Model {
    _name = "res.partner.bank";

    account_number = fields.Char();
    allow_out_payment = fields.Boolean();

    _records = [{ id: 1, account_number: "123456789", allow_out_payment: false }];
}

defineModels([ResPartnerBank]);
defineMailModels();

const arch = `
    <form>
        <field name="account_number" readonly="allow_out_payment" force_save="1"/>
        <field name="allow_out_payment" widget="trust_bank_toggle"/>
    </form>
`;

test("trusting a bank account saves it right away", async () => {
    onRpc("web_save", ({ args }) => expect.step(args[1]));
    await mountView({ type: "form", resModel: "res.partner.bank", resId: 1, arch });

    await contains(".o_field_widget[name=account_number] input").edit("987654321");
    await contains(".o_field_widget[name=allow_out_payment] input").click();
    expect.verifySteps([{ account_number: "987654321", allow_out_payment: true }]);
    expect(".o_field_widget[name=allow_out_payment] input").toBeChecked();
    expect(".o_field_widget[name=account_number] input").toHaveCount(0);

    await contains(".o_field_widget[name=allow_out_payment] input").click();
    expect.verifySteps([{ allow_out_payment: false }]);
    expect(".o_field_widget[name=account_number] input").toHaveCount(1);
});

test("trust is reverted when the bank account can't be saved", async () => {
    expect.errors(1);
    onRpc("web_save", () => {
        throw makeServerError({ type: "ValidationError", message: "Invalid account number" });
    });
    await mountView({ type: "form", resModel: "res.partner.bank", resId: 1, arch });

    await contains(".o_field_widget[name=account_number] input").edit("invalid");
    await contains(".o_field_widget[name=allow_out_payment] input").click();
    expect.verifyErrors(["Invalid account number"]);
    expect(".o_field_widget[name=allow_out_payment] input").not.toBeChecked();
    expect(".o_field_widget[name=account_number] input").toHaveValue("invalid");
});

test("trusting a new bank account doesn't save it", async () => {
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({ type: "form", resModel: "res.partner.bank", arch });

    await contains(".o_field_widget[name=allow_out_payment] input").click();
    expect.verifySteps([]);
    expect(".o_field_widget[name=allow_out_payment] input").toBeChecked();
});
