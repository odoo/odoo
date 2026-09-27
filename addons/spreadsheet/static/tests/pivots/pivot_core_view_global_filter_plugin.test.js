import { describe, expect, test } from "@odoo/hoot";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";

import { addGlobalFilterWithoutReload } from "@spreadsheet/../tests/helpers/commands";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";

describe.current.tags("headless");
defineSpreadsheetModels();

test("getFiltersMatchingPivotArgs should returns correct value for each filter", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    addGlobalFilterWithoutReload(
        model,
        {
            type: "text",
            label: "Text",
            id: "1",
        },
        {
            pivot: {
                [pivotId]: { chain: "foo", type: "char" },
            },
        }
    );
    const filters = model.getters.getFiltersMatchingPivotArgs(pivotId, [
        { field: "foo", type: "char", value: "hello" },
    ]);
    expect(filters).toEqual([{ filterId: "1", value: { operator: "ilike", strings: ["hello"] } }]);
});
