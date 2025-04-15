/** @odoo-module **/

import { click, editInput, getFixture, triggerHotkey } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("StockMoveX2ManyField", {}, function (hooks) {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                "stock.picking": {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        moves: {
                            string: "moves",
                            type: "one2many",
                            relation: "stock.move",
                        },
                        state: {
                            type: "selection",
                            selection: [
                                ["draft", "Draft"],
                                ["ready", "Ready"],
                            ],
                            default: "draft",
                            string: "State",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            state: "ready",
                            display_name: "first record",
                            moves: [1],
                        },
                    ],
                },
                "stock.move": {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        show_details_visible: {
                            string: "Show Details",
                            type: "boolean",
                            default: true,
                        },
                        lines: {
                            string: "move lines",
                            type: "one2many",
                            relation: "stock.move.line",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "test",
                        },
                    ],
                },
                "stock.move.line": {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                    },
                    records: [],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.test("pressing tab should keep focus in dialog", async function (assert) {
        assert.expect(4);
        await makeView({
            type: "form",
            resModel: "stock.picking",
            serverData,
            arch: `
                <form>
                    <header>
                        <field name="state" widget="statusbar" />
                    </header>
                    <field name="moves" widget="stock_move_one2many">
                        <tree editable="bottom">
                            <field name="display_name"/>
                            <field name="show_details_visible" column_invisible="True"/>
                        </tree>
                        <form>
                            <field name="display_name" />
                            <field name="lines">
                                <tree editable="bottom">
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            async mockRPC(route, args) {
                if (args.method === "web_save" && args.model === "stock.picking") {
                    const moveCommand = args.args[1].moves[0];
                    assert.strictEqual(moveCommand[2].display_name, "new name");
                    assert.strictEqual(moveCommand[2].lines[0][2].display_name, "example");
                }
            },
        });

        await click(target, "button[name='Open Move']");
        await click(target, ".modal-dialog .o_field_x2many_list_row_add a");
        await editInput(
            target,
            ".modal-dialog .o_list_renderer [name='display_name'] input",
            "example"
        );
        await triggerHotkey("Tab");

        const dialog = target.querySelector(".modal-dialog");
        assert.ok(
            dialog.contains(document.activeElement),
            "The focus should still be on the dialog"
        );

        await click(target, ".modal-dialog .o_form_button_save");
        await click(target, ".o_field_cell[name='display_name']");
        assert.containsNone(target ,".modal-dialog", "should not open a dialog");
        await editInput(target, "[name='display_name'] input", "new name");
        await click(target, ".o_control_panel .o_form_button_save");
    });
});
