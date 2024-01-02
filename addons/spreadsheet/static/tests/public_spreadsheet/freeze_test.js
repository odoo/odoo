/** @odoo-module */

import { freezeOdooData } from "../../src/helpers/model";
import { createSpreadsheetWithChart } from "../utils/chart";
import { setCellContent } from "../utils/commands";
import { getCell, getEvaluatedCell } from "../utils/getters";
import { createSpreadsheetWithPivot } from "../utils/pivot";
import { createModelWithDataSource } from "@spreadsheet/../tests/utils/model";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/utils/global_filter";
import { addGlobalFilter } from "@spreadsheet/../tests/utils/commands";

QUnit.module("freezing spreadsheet", {}, function () {
    QUnit.test("odoo pivot functions are replaced with their value", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        assert.strictEqual(getCell(model, "A3").content, '=ODOO.PIVOT.HEADER(1,"bar","false")');
        assert.strictEqual(
            getCell(model, "C3").content,
            '=ODOO.PIVOT(1,"probability","bar","false","foo",2)'
        );
        assert.strictEqual(getEvaluatedCell(model, "A3").value, "No");
        assert.strictEqual(getEvaluatedCell(model, "C3").value, 15);
        const data = await freezeOdooData(model);
        const cells = data.sheets[0].cells;
        assert.strictEqual(cells.A3.content, "No", "the content is replaced with the value");
        assert.strictEqual(cells.C3.content, "15.00", "the content is replaced with the value");
    });

    QUnit.test("invalid expression with pivot function", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        setCellContent(model, "A1", "=ODOO.PIVOT(1)+"); // invalid expression
        assert.strictEqual(getEvaluatedCell(model, "A1").value, "#BAD_EXPR");
        const data = await freezeOdooData(model);
        const cells = data.sheets[0].cells;
        assert.strictEqual(
            cells.A1.content,
            "=ODOO.PIVOT(1)+",
            "the content is left as is when the expression is invalid"
        );
    });

    QUnit.test("odoo pivot functions detection is not case sensitive", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        setCellContent(model, "A1", '=odoo.pivot(1,"probability")');
        setCellContent(model, "A2", '=ODOO.pivot(1,"probability")');
        const data = await freezeOdooData(model);
        const A1 = data.sheets[0].cells.A1;
        const A2 = data.sheets[0].cells.A2;
        assert.strictEqual(A1.content, "131.00", "the content is replaced with the value");
        assert.strictEqual(A2.content, "131.00", "the content is replaced with the value");
    });

    QUnit.test("computed format is exported", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
              <pivot>
                  <field name="pognon" type="measure"/>
              </pivot>
            `,
        });
        setCellContent(model, "A1", '=ODOO.PIVOT(1,"pognon")');
        assert.strictEqual(getCell(model, "A1").format, undefined);
        assert.strictEqual(getEvaluatedCell(model, "A1").format, "#,##0.00[$€]");
        const data = await freezeOdooData(model);
        const A1 = data.sheets[0].cells.A1;
        const format = data.formats[A1.format];
        assert.strictEqual(format, "#,##0.00[$€]");
    });

    QUnit.test("odoo charts are replaced with an image", async function (assert) {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
        const data = await freezeOdooData(model);
        assert.strictEqual(data.sheets[0].figures.length, 1);
        assert.strictEqual(data.sheets[0].figures[0].tag, "image");
    });

    QUnit.test("translation function are replaced with their value", async function (assert) {
        const model = await createModelWithDataSource();
        setCellContent(model, "A1", `=_t("example")`);
        setCellContent(model, "A2", `=CONCATENATE("for",_t(" example"))`);
        assert.strictEqual(getEvaluatedCell(model, "A1").value, "example");
        assert.strictEqual(getEvaluatedCell(model, "A2").value, "for example");
        const data = await freezeOdooData(model);
        const cells = data.sheets[0].cells;
        assert.strictEqual(cells.A1.content, "example", "the content is replaced with the value");
        assert.strictEqual(
            cells.A2.content,
            "for example",
            "the content is replaced with the value even when translation function is nested"
        );
    });

    QUnit.test("a new sheet is added for global filters", async function (assert) {
        const model = await createModelWithDataSource();
        await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
        const data = await freezeOdooData(model);
        assert.strictEqual(data.sheets.length, 2);
        assert.strictEqual(data.sheets[1].name, "Active Filters");
        assert.strictEqual(data.sheets[1].cells.A2.content, "This Year");
    });

    QUnit.test("global filters and their display value are exported", async function (assert) {
        const model = await createModelWithDataSource();
        await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
        const data = await freezeOdooData(model);
        assert.strictEqual(data.globalFilters.length, 1);
        assert.strictEqual(data.globalFilters[0].label, "This Year");
        assert.strictEqual(data.globalFilters[0].value, new Date().getFullYear().toString());
    });
});
