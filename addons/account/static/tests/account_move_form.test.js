import { defineAccountModels } from "./account_test_helpers";
import { test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    insertText,
    openFormView,
    start,
    startServer,
    triggerHotkey,
    step,
} from "@mail/../tests/mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

defineAccountModels();

test("When I switch tabs, it saves", async () => {
    const pyEnv = await startServer();
    const accountMove = pyEnv["account.move"].create({ name: "move0" });
    await start();
    onRpc("account.move", "web_save", () => {
        step("tab saved");
    });
    await openFormView("account.move", accountMove, {
        arch: `<form js_class='account_move_form'>
            <sheet>
                <notebook>
                    <page id="invoice_tab" name="invoice_tab" string="Invoice Lines">
                        <field name="name"/>
                    </page>
                    <page id="aml_tab" string="Journal Items" name="aml_tab"></page>
                </notebook>
            </sheet>
        </form>`,
    });
    await insertText("[name='name'] input", "somebody save me!");
    triggerHotkey("Enter");
    await click('a[name="aml_tab"]');
    await assertSteps(["tab saved"]);
});
