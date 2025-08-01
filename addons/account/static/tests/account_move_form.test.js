import {
    click,
    insertText,
    openFormView,
    start,
    startServer,
    triggerHotkey
} from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { asyncStep, contains, defineModels, fields, onRpc, models, waitForSteps} from "@web/../tests/web_test_helpers";
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
class AccountMove extends models.Model {
    line_ids = fields.One2many({
        string: "Invoice Lines",
        relation: "account.move.line",
    })

    _records = [{ id: 1, name: "account.move" }]
}
class AccountMoveLine extends models.Model {
    name = fields.Char();
    product_id = fields.Many2one({
        string:"Product",
        relation:"product",
    });
    move_id = fields.Many2one({
        string: "Account Move",
        relation: "account.move",
    })
}
class Product extends models.Model {
    name = fields.Char();
    _records = [{ id: 1, name: "testProduct" }];
}

defineModels({ Product, AccountMoveLine, AccountMove });

test("Update description on product line", async() => {
    const pyEnv = await startServer();
    const productId = pyEnv["product"].browse([1]);
    const accountMove = pyEnv["account.move"].browse([1]);
    pyEnv["account.move.line"].create({ name: productId[0].name, product_id: productId[0].id, move_id: accountMove[0].id });
    await start();
    onRpc("account.move", "web_save", () => { asyncStep("save")});
    await openFormView("account.move", accountMove[0].id, {
        arch: `<form js_class="account_move_form">
            <sheet>
                <notebook>
                    <page id="invoice_tab" name="invoice_tab" string="Invoice Lines">
                        <field name="invoice_line_ids" mode="list" widget="product_label_section_and_note_field_o2m">
                            <list name="journal_items" editable="bottom" string="Journal Items">
                                <field name="product_id" widget="product_label_section_and_note_field" readonly="0"/>
                                <field name="name" widget="section_and_note_text" optional="show"/>
                            </list>
                        </field>
                    </page>
                </notebook>
            </sheet>
        </form>`,
    });

    await click(".o_many2one");
    await contains("#labelVisibilityButtonId").click()
    await insertText("textarea[placeholder='Enter a description']", "testDescription");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);

    const line = pyEnv["account.move.line"].browse([1])[0];
    expect(line.name).toBe("testProduct\ntestDescription");

});
