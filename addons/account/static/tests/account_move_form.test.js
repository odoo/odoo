import { AccountMoveFormNotebook } from "@account/components/account_move_form/account_move_form";
import {
    click,
    insertText,
    openFormView,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    asyncStep,
    contains,
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

import { defineAccountModels } from "./account_test_helpers.js";

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
    expect(".o_dialog div.text-danger").toHaveText(
        "This operation will create a gap in the sequence.",
        {
            message: "warning message has been added in the dialog",
        },
    );
});
class AccountMove extends models.Model {
    line_ids = fields.One2many({
        string: "Invoice Lines",
        relation: "account.move.line",
    });

    _records = [{ id: 1, name: "account.move" }];
}
class AccountMoveLine extends models.Model {
    name = fields.Char();
    product_id = fields.Many2one({
        string: "Product",
        relation: "product",
    });
    move_id = fields.Many2one({
        string: "Account Move",
        relation: "account.move",
    });
}
class Product extends models.Model {
    name = fields.Char();
    _records = [{ id: 1, name: "testProduct" }];
}

defineModels({ Product, AccountMoveLine, AccountMove });

test("Update description on product line", async () => {
    const pyEnv = await startServer();
    const productId = pyEnv["product"].browse([1]);
    const accountMove = pyEnv["account.move"].browse([1]);
    pyEnv["account.move.line"].create({
        name: productId[0].name,
        product_id: productId[0].id,
        move_id: accountMove[0].id,
    });
    await start();
    onRpc("account.move", "web_save", () => {
        asyncStep("save");
    });
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
    await contains("#labelVisibilityButtonId").click();
    await insertText("textarea[placeholder='Enter a description']", "testDescription");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);

    const line = pyEnv["account.move.line"].browse([1])[0];
    expect(line.name).toBe("testProduct\ntestDescription");
});

test("account tab activation flushes inputs and discards a hidden page after saving", async () => {
    const saved = new Deferred();
    class Parent extends Component {
        static props = ["*"];
        static components = { AccountMoveFormNotebook };
        static template = xml`
            <AccountMoveFormNotebook onWillActivatePage="() => this.flush()" onBeforeTabSwitch="() => this.save()">
                <t t-set-slot="a" title="'A'" isVisible="true"><div class="page-a"/></t>
                <t t-set-slot="b" title="'B'" isVisible="!state.hidden"><div class="page-b"/></t>
            </AccountMoveFormNotebook>`;
        setup() {
            this.state = useState({ hidden: false });
        }
        flush() {
            expect.step("flush");
        }
        save() {
            expect.step("save");
            return saved;
        }
    }
    const parent = await mountWithCleanup(Parent);
    await click(".nav-item:nth-child(2) .nav-link");
    expect.verifySteps(["flush", "save"]);
    parent.state.hidden = true;
    await animationFrame();
    saved.resolve();
    await animationFrame();
    expect(".nav-link.active").toHaveText("A");
    expect(".page-b").toHaveCount(0);
});

for (const blockedAt of ["flush", "save"]) {
    test(`account tab activation can be refused by ${blockedAt}`, async () => {
        class Parent extends Component {
            static props = ["*"];
            static components = { AccountMoveFormNotebook };
            static template = xml`
                <AccountMoveFormNotebook onWillActivatePage="() => this.flush()" onBeforeTabSwitch="() => this.save()">
                    <t t-set-slot="a" title="'A'" isVisible="true">A</t>
                    <t t-set-slot="b" title="'B'" isVisible="true">B</t>
                </AccountMoveFormNotebook>`;
            flush() {
                expect.step("flush");
                return blockedAt !== "flush";
            }
            save() {
                expect.step("save");
                return false;
            }
        }
        await mountWithCleanup(Parent);
        await click(".nav-item:nth-child(2) .nav-link");
        expect.verifySteps(blockedAt === "flush" ? ["flush"] : ["flush", "save"]);
        expect(".nav-link.active").toHaveText("A");
    });
}
