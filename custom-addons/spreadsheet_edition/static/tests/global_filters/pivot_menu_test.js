/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";

import { addGlobalFilter, selectCell } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";
import { getCellContent } from "@spreadsheet/../tests/utils/getters";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";
import * as spreadsheet from "@odoo/o-spreadsheet";

const { topbarMenuRegistry } = spreadsheet.registries;

QUnit.module("spreadsheet_edition > menu", {}, () => {
    QUnit.test(
        "Re-insert a pivot with a global filter should re-insert the full pivot",
        async function (assert) {
            assert.expect(1);

            const { model, env } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="name" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            await addGlobalFilter(model, {
                id: "41",
                type: "relation",
                label: "41",
                defaultValue: [41],
            });
            selectCell(model, "A6");
            const reinsertPivotPath = [
                "data",
                "insert_pivot",
                "reinsert_pivot",
                "reinsert_pivot_1",
            ];
            await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
            await nextTick();
            assert.equal(getCellContent(model, "B6"), getCellContent(model, "B1"));
        }
    );
});
