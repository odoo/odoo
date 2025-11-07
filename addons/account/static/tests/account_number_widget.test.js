import { defineAccountNumberModels } from "./account_number_widget_test_helpers";
import { DELAY } from "@account/components/account_number_widget/account_number_widget";
import { test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import {
    click,
    contains,
    insertText,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

defineAccountNumberModels();

const validIban = "BE12651194580992";
const validClabe = "002010077777777771";
const invalidAccountNumber = "invalidAccountNumber!";

test.tags("focus required");
test("Account Number Widget full flow", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Awesome partner" });
    const bankId = pyEnv["res.partner.bank"].create({ account_number: "", partner_id: partnerId });
    await start();
    onRpc("res.partner.bank", "retrieve_account_type", (params) => {
        const account_number = params.args[0].replace(/\s/g, "");
        switch (account_number) {
            case validIban:
                return "iban";
            case validClabe:
                return "clabe";
            default:
                return "bank";
        }
    });
    await openFormView("res.partner.bank", bankId, {
        arch: `<form>
                <sheet>
                    <group>
                        <field name="account_number" widget="account_number"/>
                    </group>
                </sheet>
            </form>`,
    });
    await contains(".o_input");
    await contains(".o_account_number", { count: 0 }); // "Shouldn't display any validation icon"
    await insertText(".o_input", invalidAccountNumber, { replace: true });
    await contains(".o_account_number", { count: 0 }); // "Shouldn't change its state of display"
    await advanceTime(DELAY);
    await contains(".o_account_number", { count: 0 }); // "Shouldn't contain a validation icon for invalid account number 400ms after edition"
    await click(".o_form_button_save");
    await contains(".o_account_number", { count: 0 }); // "Shouldn't contain a validation icon for invalid account number at any time"
    await advanceTime(DELAY);
    await insertText(".o_input", validIban, { replace: true });
    await contains(".o_account_number", { count: 0 }); // "Shouldn't change its state of display"
    await advanceTime(DELAY);
    await contains(".o_account_number"); // "Should contain a validation icon 400ms after edition"
    await contains(".o_account_number i.fa.fa-check"); // "The validation icon should be the successful one"
    await click(".o_form_button_save");
    await advanceTime(DELAY);
    await contains(".o_account_number"); // "Should display validation icon at all time even when not editing"
    await insertText(".o_input", invalidAccountNumber, { replace: true });
    await advanceTime(DELAY);
    await contains(".o_account_number", { count: 0 }); // "Shouldn't contain a validation icon for invalid account number"
    await insertText(".o_input", validClabe, { replace: true });
    await advanceTime(DELAY);
    await contains(".o_account_number"); // "Shouldn't contain a validation icon for valid CLABE"
});
