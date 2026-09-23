/** @odoo-module native */
import { defineAccountIbanModels } from "./account_iban_test_helpers.js";
import { DELAY } from "@account_iban/components/iban_widget/iban_widget";
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

defineAccountIbanModels();

const validIban = "BE12651194580992";
const invalidIban = "invalidIban!";

test.tags("focus required");
test("Iban Widget full flow", async () => {
    const pyEnv = await startServer();
    const bankId = pyEnv["res.partner.bank.account"].create({ acc_number: "" });
    const partnerId = pyEnv["res.partner"].create({
        name: "Awesome partner",
        bank_account_ids: [bankId],
    });
    await start();
    onRpc("res.partner.bank.account", "is_valid_iban", (params) => {
        const iban = params.args[1].replace(/\s/g, "");
        return iban === validIban;
    });
    await openFormView("res.partner", partnerId, {
        arch: `<form>
                <sheet>
                    <group>
                        <field name="name"/>
                    </group>
                    <field name="bank_account_ids">
                        <list editable="bottom">
                            <field name="acc_number" widget="iban"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
    });
    await contains("td.o_iban_cell");
    await contains(".o_iban", { count: 0 }); // "Shouldn't display any validation icon while not editing a specific line"
    await click("td.o_iban_cell");
    await contains(".o_iban_input_with_validator");
    await contains(".o_iban", { count: 0 }); // "Shouldn't display any validation icon while iban is empty"
    await insertText(".o_iban_input_with_validator", invalidIban, { replace: true });
    await contains(".o_iban", { count: 0 }); // "Shouldn't change its state of display before edition is finished"
    await advanceTime(DELAY);
    await contains(".o_iban"); // "Should contain a validation icon 400ms after edition"
    await contains("i.fa-solid.fa-times.o_iban_fail"); // "The validation icon should be the failed one"
    await contains("i.fa-solid.fa-check.o_iban", { count: 0 }); // "The validation icon shouldn't be the successful one"
    await click(".o_form_button_save");
    await contains(".o_iban", { count: 0 }); // "Shouldn't display any validation while not editing"
    await click("td.o_iban_cell");
    await contains(".o_iban_input_with_validator");
    await advanceTime(DELAY);
    await contains("i.fa-solid.fa-times.o_iban_fail"); // "The validation icon should be present while clicking on an already filled IBAN"
    await insertText(".o_iban_cell .o_input", validIban, { replace: true });
    await contains("i.fa-solid.fa-times.o_iban_fail"); // "The validation icon shouldn't change during the edition"
    await advanceTime(DELAY);
    await contains(".o_iban"); // "Should contain a validation icon 400ms after edition"
    await contains("i.fa-solid.fa-check.o_iban"); // "The validation icon should be the successful one"
    await contains("i.fa-solid.fa-times.o_iban_fail", { count: 0 }); // "The validation icon shouldn't be the failed one"
    await click(".o_form_button_save");
    await contains(".o_iban", { count: 0 }); // "Shouldn't display any validation while not editing"
});
