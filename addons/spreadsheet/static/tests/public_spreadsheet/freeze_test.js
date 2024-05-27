/** @odoo-module */

import { freezeOdooData } from "../../src/helpers/model";
import { createSpreadsheetWithChart } from "../utils/chart";
import { setCellContent, setCellFormat } from "../utils/commands";
import { getCell, getEvaluatedCell } from "../utils/getters";
import { createModelWithDataSource } from "../utils/model";
import { createSpreadsheetWithPivot } from "../utils/pivot";
import { registry } from "@web/core/registry";
import { menuService } from "@web/webclient/menus/menu_service";
import { spreadsheetLinkMenuCellService } from "@spreadsheet/ir_ui_menu/index";
import { getMenuServerData } from "@spreadsheet/../tests/links/menu_data_utils";

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
        assert.strictEqual(cells.C3.content, "15", "the content is replaced with the value");
        assert.strictEqual(data.formats[cells.C3.format], "#,##0.00");
    });

    QUnit.test("values are not exported formatted", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        assert.strictEqual(getCell(model, "A3").content, '=ODOO.PIVOT.HEADER(1,"bar","false")');
        assert.strictEqual(
            getCell(model, "C3").content,
            '=ODOO.PIVOT(1,"probability","bar","false","foo",2)'
        );
        setCellFormat(model, "C3", "mmmm yyyy");
        setCellContent(model, "C4", "=C3+31");
        assert.strictEqual(getEvaluatedCell(model, "C3").value, 15);
        assert.strictEqual(getEvaluatedCell(model, "C3").formattedValue, "January 1900");
        assert.strictEqual(getEvaluatedCell(model, "C4").value, 46);
        assert.strictEqual(getEvaluatedCell(model, "C4").formattedValue, "February 1900");
        const data = await freezeOdooData(model);
        const sharedModel = await createModelWithDataSource({ spreadsheetData: data });
        assert.strictEqual(getEvaluatedCell(sharedModel, "C3").value, 15);
        assert.strictEqual(getEvaluatedCell(sharedModel, "C3").formattedValue, "January 1900");
        assert.strictEqual(getEvaluatedCell(sharedModel, "C4").value, 46);
        assert.strictEqual(getEvaluatedCell(sharedModel, "C4").formattedValue, "February 1900");
    });

    QUnit.test("odoo pivot functions detection is not case sensitive", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        setCellContent(model, "A1", '=odoo.pivot(1,"probability")');
        setCellContent(model, "A2", '=ODOO.pivot(1,"probability")');
        const data = await freezeOdooData(model);
        const A1 = data.sheets[0].cells.A1;
        const A2 = data.sheets[0].cells.A2;
        assert.strictEqual(A1.content, "131", "the content is replaced with the value");
        assert.strictEqual(A2.content, "131", "the content is replaced with the value");
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

    QUnit.test("odoo links are replaced with their label", async function(assert){
        const view = {
            name: "an odoo view",
            viewType: "list",
            action: {
                modelName: "partner",
                views: [[false, "list"]],
            },
        };
        const data = {
            sheets: [
                {
                    cells: {
                        A1: { content: "[menu_xml](odoo://ir_menu_xml_id/test_menu)" },
                        A2: { content: "[menu_id](odoo://ir_menu_id/12)" },
                        A3: { content: `[odoo_view](odoo://view/${JSON.stringify(view)})` },
                        A4: { content: "[external_link](https://odoo.com)" } ,
                        A5: { content: "[internal_link](o-spreadsheet://Sheet1)"}
                    },

                },
            ],
        };
      registry.category("services")
          .add("menu", menuService)
          .add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);

        const model = await createModelWithDataSource({ spreadsheetData: data, serverData: getMenuServerData() });
        const frozenData = await freezeOdooData(model);
        assert.strictEqual(frozenData.sheets[0].cells.A1.content, "menu_xml");
        assert.strictEqual(frozenData.sheets[0].cells.A2.content, "menu_id");
        assert.strictEqual(frozenData.sheets[0].cells.A3.content, "odoo_view");
        assert.strictEqual(frozenData.sheets[0].cells.A4.content, "[external_link](https://odoo.com)");
        assert.strictEqual(frozenData.sheets[0].cells.A5.content, "[internal_link](o-spreadsheet://Sheet1)");
    });
});
