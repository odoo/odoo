/** @odoo-module */

import {
    click,
    getFixture,
    nextTick,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { hoverGridCell } from "@web_grid/../tests/helpers";

let serverData, target;

QUnit.module("consolidation_grid", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                "consolidation.journal": {
                    fields: {
                        name: {
                            string: "Consolidation Journal Name",
                            type: "string",
                        },
                        auto_generated: { string: "Is Auto-generated?", type: "boolean" },
                    },
                    records: [
                        { id: 1, name: "foo", auto_generated: true },
                        { id: 2, name: "boo", auto_generated: false },
                    ],
                },
                "consolidation.account": {
                    fields: {
                        name: {
                            string: "Consolidation Account Name",
                            type: "string",
                        },
                    },
                    records: [
                        { id: 1, name: "Account 1" },
                        { id: 2, name: "Account 2" },
                    ],
                },
                "consolidation.journal.line": {
                    fields: {
                        journal_id: {
                            string: "Consolidation",
                            type: "many2one",
                            relation: "consolidation.journal",
                        },
                        account_id: {
                            string: "Account",
                            type: "many2one",
                            relation: "consolidation.account",
                        },
                        amount: { string: "Amount", type: "float", group_operator: "sum" },
                    },
                    records: [
                        { id: 1, journal_id: 1, account_id: 1, amount: 2500 },
                        { id: 2, journal_id: 2, account_id: 2, amount: 250.5 },
                    ],
                },
            },
            views: {
                "consolidation.journal.line,false,grid": `
                    <grid js_class="consolidation_grid" editable="1" create="0">
                        <field name="account_id" type="row"/>
                        <field name="journal_id" type="col"/>
                        <field name="amount" type="measure" widget="float"/>
                    </grid>`,
                "consolidation.journal,false,form": `
                    <form>
                        <group>
                            <group>
                                <field name="name"/>
                            </group>
                        </group>
                    </form>`,
            },
        };

        setupViewRegistries();
        target = getFixture();
    });

    QUnit.test("cell is readonly if journal is auto-generated", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "consolidation.journal.line",
            serverData,
        });

        const cells = target.querySelectorAll(
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_row_total,.o_grid_column_total)"
        );

        assert.strictEqual(cells.length, 4, "4 cells should be selected");
        const readonlyCell = target.querySelector(".o_grid_row[data-row='1'][data-column='0']");
        await hoverGridCell(readonlyCell);
        await nextTick();
        if (!target.querySelectorAll(".o_grid_cell span").length) {
            await nextTick();
        }
        assert.containsOnce(target, "div.o_grid_cell.o_field_cursor_disabled");
        await click(target, ".o_grid_cell");
        assert.containsNone(target, "o_grid_cell input");
        assert.strictEqual(
            readonlyCell.textContent,
            "2500.00",
            "The cell should be the one with 2500 as amount and so the one in foo journal and Account 1"
        );
        await triggerEvent(target, ".o_grid_cell", "mouseout");

        let emptyCell = target.querySelector(".o_grid_row[data-row='2'][data-column='0']");
        await hoverGridCell(emptyCell);
        if (!target.querySelectorAll(".o_grid_cell span").length) {
            await nextTick();
        }
        assert.containsOnce(target, "div.o_grid_cell.o_field_cursor_disabled");
        await click(target, ".o_grid_cell span");
        assert.containsNone(target, "div.o_grid_cell input");
        assert.strictEqual(
            emptyCell.textContent,
            "0.00",
            "Even if the cell is empty, the cell should be editable since the column is not readonly (journal boo is not auto-generated)"
        );
        await triggerEvent(target, ".o_grid_cell", "mouseout");

        const editableCell = target.querySelector(".o_grid_row[data-row='2'][data-column='1']");
        await hoverGridCell(editableCell);
        await nextTick();
        assert.containsNone(target, "div.o_grid_cell.o_field_cursor_disabled");
        await click(target, ".o_grid_cell");
        await nextTick();
        assert.containsOnce(target, "div.o_grid_cell input");
        assert.strictEqual(
            editableCell.textContent,
            "250.50",
            "The cell should be the one with 250.50 as amount and so the one in boo journal and Account 1"
        );
        await triggerEvent(target, ".o_grid_cell", "mouseout");
        await triggerEvent(target, ".o_grid_cell", "keydown", { key: "escape" });

        emptyCell = target.querySelector(".o_grid_row[data-row='1'][data-column='1']");
        await hoverGridCell(emptyCell);
        await nextTick();
        assert.containsNone(target, "div.o_grid_cell.o_field_cursor_disabled");
        await click(target, ".o_grid_cell");
        await nextTick();
        assert.containsOnce(target, "div.o_grid_cell input");
        assert.strictEqual(
            emptyCell.textContent,
            "0.00",
            "Even if the cell is empty, the cell should be in readonly since the column is readonly (journal is not auto-generated)"
        );
        await triggerEvent(target, ".o_grid_cell", "keydown", { key: "escape" });
    });

    QUnit.test("consolidation_grid: add column button should be hidden if no default journal in context", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "consolidation.journal.line",
            serverData,
        });

        assert.containsNone(
            target,
            ".o_grid_button_add_column",
            "No 'Add a column' button should be displayed since no 'default_journal_id' is defined in the context"
        );
    })

    QUnit.test("consolidation_grid: add column", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "consolidation.journal.line",
            serverData,
            context: { default_period_id: 1 },
        });

        assert.containsN(
            target,
            ".o_grid_button_add_column",
            2, // one button is not displayed (responsive)
            "'Add a column' button should be displayed in the view since 'default_period_id' is defined in the context."
        );
    })
});
