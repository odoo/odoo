/** @odoo-module */

import { setCellContent, setSelection } from "@spreadsheet/../tests/utils/commands";
import { getCellFormula } from "@spreadsheet/../tests/utils/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";

QUnit.module("documents_spreadsheet > autofill template", {}, () => {
    QUnit.test("Autofill template position", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="bar" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(
            model,
            "B2",
            `=ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 9999),"bar",ODOO.PIVOT.POSITION("1","bar", 4444))`
        );

        // DOWN
        setSelection(model, "B2");

        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
        model.dispatch("AUTOFILL");
        assert.equal(
            getCellFormula(model, "B3"),
            `=ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 10000),"bar",ODOO.PIVOT.POSITION("1","bar", 4444))`
        );

        // UP
        setSelection(model, "B2");

        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 0 });
        model.dispatch("AUTOFILL");
        assert.equal(
            getCellFormula(model, "B1"),
            `=ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 9998),"bar",ODOO.PIVOT.POSITION("1","bar", 4444))`
        );

        // RIGHT
        setSelection(model, "B2");

        model.dispatch("AUTOFILL_SELECT", { col: 2, row: 1 });
        model.dispatch("AUTOFILL");
        assert.equal(
            getCellFormula(model, "C2"),
            `=ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 9999),"bar",ODOO.PIVOT.POSITION("1","bar", 4445))`
        );

        // LEFT
        setSelection(model, "B2");

        model.dispatch("AUTOFILL_SELECT", { col: 0, row: 1 });
        model.dispatch("AUTOFILL");
        assert.equal(
            getCellFormula(model, "A2"),
            `=ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 9999),"bar",ODOO.PIVOT.POSITION("1","bar", 4443))`
        );
    });

    QUnit.test("Autofill template position: =-PIVOT(...)", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="bar" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(
            model,
            "B2",
            `= - ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 9999),"bar",ODOO.PIVOT.POSITION("1","bar", 4444))`
        );

        // DOWN
        setSelection(model, "B2");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
        model.dispatch("AUTOFILL");
        assert.equal(
            getCellFormula(model, "B3"),
            `= - ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 10000),"bar",ODOO.PIVOT.POSITION("1","bar", 4444))`
        );
    });

    QUnit.test("Autofill template position: 2 PIVOT in one formula", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `<pivot>
                <field name="bar" type="col"/>
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        });
        setCellContent(
            model,
            "B2",
            `=SUM(
                ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 9999),"bar",ODOO.PIVOT.POSITION("1","bar", 4444)),
                ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 666),"bar",ODOO.PIVOT.POSITION("1","bar", 4444))
            )`.replace(/\n/g, "")
        );

        setSelection(model, "B2");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
        model.dispatch("AUTOFILL");
        // Well this does not work, it only updates the last PIVOT figure. But at least it does not crash.
        assert.equal(
            getCellFormula(model, "B3"),
            `=SUM(
                ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 9999),"bar",ODOO.PIVOT.POSITION("1","bar", 4444)),
                ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 667),"bar",ODOO.PIVOT.POSITION("1","bar", 4444))
            )`.replace(/\n/g, "")
        );
    });

    QUnit.test("Autofill template position: PIVOT.POSITION not in PIVOT", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="bar" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "B2", `=ODOO.PIVOT.POSITION("1","foo", 3333)`);

        // DOWN
        setSelection(model, "B2");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
        model.dispatch("AUTOFILL");
        assert.equal(
            getCellFormula(model, "B3"),
            `=ODOO.PIVOT.POSITION("1","foo", 3333)`,
            "Should have copied the origin value"
        );
    });

    QUnit.test("Autofill template position: with invalid pivot id", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="bar" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(
            model,
            "B2",
            `=ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("10000","product_id", 9999))`
        );

        // DOWN
        setSelection(model, "B2");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
        model.dispatch("AUTOFILL");
        assert.equal(
            getCellFormula(model, "B3"),
            `=ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("10000","product_id", 9999))`,
            "Should have copied the origin value"
        );
    });

    QUnit.test("Autofill template position: increment last group", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="bar" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(
            model,
            "B2",
            `=ODOO.PIVOT("1","probability","foo",ODOO.PIVOT.POSITION("1","foo", 3333),"product_id",ODOO.PIVOT.POSITION("1","product_id", 9999),"bar",ODOO.PIVOT.POSITION("1","bar", 4444))`
        );

        // DOWN
        setSelection(model, "B2");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
        model.dispatch("AUTOFILL");
        assert.equal(
            getCellFormula(model, "B3"),
            `=ODOO.PIVOT("1","probability","foo",ODOO.PIVOT.POSITION("1","foo", 3333),"product_id",ODOO.PIVOT.POSITION("1","product_id", 10000),"bar",ODOO.PIVOT.POSITION("1","bar", 4444))`,
            "It should have incremented the last row group position"
        );
    });

    QUnit.test(
        "Autofill template position: does not increment last field if not many2one",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                    <pivot>
                        <field name="bar" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="foo" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            // last row field (foo) is not a position
            setCellContent(
                model,
                "B2",
                `=ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 9999), "foo","10","bar","15")`
            );

            // DOWN
            setSelection(model, "B2");
            model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "B3"),
                `=ODOO.PIVOT("1","probability","product_id",ODOO.PIVOT.POSITION("1","product_id", 9999), "foo","10","bar","15")`,
                "It should not have changed the formula"
            );
        }
    );
});
