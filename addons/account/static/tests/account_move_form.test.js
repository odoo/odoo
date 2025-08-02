import {
    click,
    insertText,
    openFormView,
    start,
    startServer,
    triggerHotkey
} from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { asyncStep, contains, onRpc, waitForSteps } from "@web/../tests/web_test_helpers";
import { defineAccountModels } from "./account_test_helpers";

defineAccountModels();

test("When I switch tabs, it saves", async () => {
    const pyEnv = await startServer();
    const accountMove = pyEnv["account.move"].create({ name: "move0" });
    await start();
    onRpc("account.move", "web_save", () => {
        asyncStep("tab saved");
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
    await click('button[name="aml_tab"]');
    await waitForSteps(["tab saved"]);
});

test("Confirmation dialog on delete contains a warning", async () => {
    const pyEnv = await startServer();
    const accountMove = pyEnv["account.move"].create({ name: "move0" });
    await start();
    onRpc("account.move", "check_move_sequence_chain", () => {
        return false;
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
    await contains(".o_cp_action_menus button").click();
    await contains(".o_menu_item:contains(Delete)").click();
    expect(".o_dialog div.text-danger").toHaveText("This operation will create a gap in the sequence.", {
        message: "warning message has been added in the dialog"
    });
});
