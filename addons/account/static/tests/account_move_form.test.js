import {
    click,
    insertText,
    openFormView,
    patchUiSize,
    SIZES,
    start,
    startServer,
    triggerHotkey
} from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
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
    await click('a[name="aml_tab"]');
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

test("Display main_attachment if no attachments", async () => {
    const pyEnv = await startServer();
    const pdfId = pyEnv["ir.attachment"].create({
        mimetype: "application/pdf",
    });
    const accountMove = pyEnv["account.move"].create({
        name: "Rick Astley",
        message_attachment_count: 0,
    });
    pyEnv["mail.message"].create([
        {
            body: "Never Gonna Give You Up, Never Gonna Let You Down, Never Gonna Run Around and Desert You.",
            res_id: accountMove,
            model: "account.move",
            attachment_ids: [pdfId],
        },
    ]);
    pyEnv["account.move"].write([accountMove], { message_main_attachment_id: pdfId });

    patchUiSize({ size: SIZES.XXL });
    await start();
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
            <div class="o_attachment_preview"/>
            <chatter/>
        </form>`,
    });
    await waitFor(".o_attachment_preview");
    expect(".o-mail-Attachment > iframe").toBeVisible(); // There should be iframe for PDF viewer
});
