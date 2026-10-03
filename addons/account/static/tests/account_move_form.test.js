import {
    click,
    insertText,
    openFormView,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, onRpc, models} from "@web/../tests/web_test_helpers";
import { defineAccountModels } from "./account_test_helpers";

defineAccountModels();

test("When I switch tabs, it saves", async () => {
    const pyEnv = await startServer();
    const accountMove = pyEnv["account.move"].create({ name: "move0" });
    await start();
    onRpc("account.move", "web_save", () => {
        expect.step("tab saved");
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
    await expect.waitForSteps(["tab saved"]);
});

test("Confirmation dialog on delete contains a warning", async () => {
    const pyEnv = await startServer();
    const accountMove = pyEnv["account.move"].create({ name: "move0" });
    await start();
    onRpc("account.move", "check_move_sequence_chain", () => false);
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
    expect(".o_dialog div.alert.alert-warning").toHaveText(
        "This operation will create a gap in the sequence.",
        { message: "warning message has been added in the dialog" }
    );
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
        string: "Journal Entry",
        relation: "account.move",
    })
    account_id = fields.Many2one({
        string: "Account",
        relation: "account.account",
    })
}
class Product extends models.Model {
    name = fields.Char();
    _records = [{ id: 1, name: "testProduct" }];
}
class AccountAccount extends models.Model {
    _name = "account.account";

    name = fields.Char();
    code = fields.Char();

    _records = [{ id: 1, name: "Outstanding Receipts", code: "101200" }];
    _views = {
        form: `<form><field name="name"/><field name="code"/></form>`,
        kanban: `<kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>`,
    };
}

defineModels({ Product, AccountMoveLine, AccountMove, AccountAccount });

test("Update description on product line", async() => {
    const pyEnv = await startServer();
    const productId = pyEnv["product"].browse([1]);
    const accountMove = pyEnv["account.move"].browse([1]);
    pyEnv["account.move"].write([accountMove[0].id], {
        invoice_line_ids: [[0, 0, { name: productId[0].name, product_id: productId[0].id }]],
    });
    await start();
    onRpc("account.move", "web_save", () => { expect.step("save")});
    await openFormView("account.move", accountMove[0].id, {
        arch: `<form js_class="account_move_form">
            <sheet>
                <notebook>
                    <page id="invoice_tab" name="invoice_tab" string="Invoice Lines">
                        <field name="invoice_line_ids" mode="list" widget="product_label_section_and_note_field_o2m">
                            <list name="journal_items" editable="bottom" string="Journal Items">
                                <field name="product_id" widget="product_label_section_and_note_field" readonly="0"/>
                                <field name="name" widget="account_label_text" optional="show"/>
                            </list>
                        </field>
                    </page>
                </notebook>
            </sheet>
        </form>`,
    });

    await click(".o_many2one");
    await insertText("textarea[placeholder='Enter a description']", "testDescription");
    await click(".o_form_button_save");
    await expect.waitForSteps(["save"]);

    const line = pyEnv["account.move.line"].browse([1])[0];
    expect(line.name).toBe("testProduct\ntestDescription");
});

test.tags("mobile");
test("many2one in line inside dialog does not save or reload line when opening related record", async () => {
    await startServer();

    onRpc("get_formview_id", () => false);
    onRpc("account.move.line", "web_save", () => {
        expect.step("aml_web_save");
    });
    onRpc("account.move.line", "web_read", () => {
        expect.step("aml_web_read");
    });
    onRpc("account.account", "web_save", () => {
        expect.step("account_web_save");
    });

    await start();

    await openFormView("account.move", 1, {
        arch: `<form js_class="account_move_form">
            <sheet>
                <notebook>
                    <page id="aml_tab" name="aml_tab" string="Journal Items">
                        <field name="line_ids" mode="kanban" add-label="Add Journal Items">
                            <kanban>
                                <templates>
                                    <t t-name="card">
                                        <field name="account_id"/>
                                    </t>
                                </templates>
                            </kanban>
                            <form string="Create Journal Items">
                                <field name="account_id"/>
                                <field name="name"/>
                            </form>
                        </field>
                    </page>
                </notebook>
            </sheet>
        </form>`,
    });

    expect("button:contains(Add Journal Items)").toHaveCount(1);
    await contains("button:contains(Add Journal Items)").click();

    expect(".o_dialog").toHaveCount(1);

    await contains(".o_dialog .o_field_widget[name=account_id] input").click();
    await contains(".o_select_create_dialog_content .o_kanban_record").click();

    expect(".o_dialog").toHaveCount(1);

    expect(".o_dialog .o_field_widget[name=account_id] .o_external_button").toHaveCount(1);
    await contains(".o_dialog .o_field_widget[name=account_id] .o_external_button").click();

    expect(".o_dialog").toHaveCount(2);
    expect.verifySteps([]);
});

