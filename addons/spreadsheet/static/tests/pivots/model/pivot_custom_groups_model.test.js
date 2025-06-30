import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { registries } from "@odoo/o-spreadsheet";
import { setCellContent, setSelection, updatePivot } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { getEvaluatedCell, getFormattedValueGrid } from "@spreadsheet/../tests/helpers/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { Partner, Product } from "../../helpers/data";
const { cellMenuRegistry } = registries;

describe.current.tags("headless");
defineSpreadsheetModels();

beforeEach(() => {
    Product._records.push(
        { id: 200, display_name: "chair", name: "chair" },
        { id: 201, display_name: "table", name: "table" }
    );
    Partner._records.push(
        { id: 200, foo: 12, bar: true, product_id: 200, probability: 100, currency_id: 1 },
        { id: 201, foo: 13, bar: false, product_id: 201, probability: 50, currency_id: 1 }
    );
});

describe("Pivot custom groups", () => {
    test("Can have custom groups in a pivot", async function () {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "GroupedProducts", order: "asc" }],
            rows: [],
            measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
            customFields: {
                GroupedProducts: {
                    parentField: "product_id",
                    name: "GroupedProducts",
                    groups: [{ name: "A Group", values: [37, 41] }],
                },
            },
        });
        await waitForDataLoaded(model);
        setCellContent(model, "A1", "=PIVOT(1)");

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:E3")).toEqual({
            A1:"Partner Pivot",  B1: "A Group",      C1: "chair",        D1: "table",        E1: "Total",
            A2: "",              B2: "Probability",  C2: "Probability",  D2: "Probability",  E2: "Probability",
            A3: "Total",         B3: "131.00",       C3: "100.00",       D3: "50.00",        E3: "281.00",
        });
    });

    test("Can have custom groups on char field", async function () {
        Partner._records = Partner._records.map((record, i) => ({
            ...record,
            name: `Partner${i + 1}`,
        }));
        const { model, pivotId } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [],
            rows: [{ fieldName: "GroupedNames", order: "asc" }],
            measures: [{ id: "probability:min", fieldName: "probability", aggregator: "min" }],
            customFields: {
                GroupedNames: {
                    parentField: "name",
                    name: "GroupedNames",
                    groups: [{ name: "First Three", values: ["Partner1", "Partner2", "Partner3"] }],
                },
            },
        });
        await waitForDataLoaded(model);
        setCellContent(model, "A1", "=PIVOT(1)");

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:B7")).toEqual({
            A1:"Partner Pivot",  B1: "Total",
            A2: "",              B2: "Probability",
            A3: "First Three",   B3: "10.00",
            A4: "Partner4",      B4: "15.00",
            A5: "Partner5",      B5: "100.00",
            A6: "Partner6",      B6: "50.00",
            A7: "Total",         B7: "10.00",
        });
    });

    test('Cannot have custom groups with "count_distinct" measure', async function () {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "GroupedProducts", order: "asc" }],
            rows: [],
            measures: [
                {
                    id: "probability:count_distinct",
                    fieldName: "probability",
                    aggregator: "count_distinct",
                },
            ],
            customFields: {
                GroupedProducts: {
                    parentField: "product_id",
                    name: "GroupedProducts",
                    groups: [{ name: "A Group", values: [37, 41] }],
                },
            },
        });
        await waitForDataLoaded(model);
        setCellContent(model, "A1", "=PIVOT(1)");

        const cell = getEvaluatedCell(model, "A1");
        expect(cell.value).toEqual("#ERROR");
        expect(cell.message).toEqual(
            'Cannot use custom pivot groups with "Count Distinct" measure'
        );
        const pivot = model.getters.getPivot(pivotId);
        expect(pivot.definition.measures[0].isValid).toBe(false);
    });

    test("Can have both the grouped field and the base field at the same time in the pivot", async function () {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "GroupedProducts", order: "asc" }],
            rows: [{ fieldName: "product_id", order: "asc" }],
            measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
            customFields: {
                GroupedProducts: {
                    parentField: "product_id",
                    name: "GroupedProducts",
                    groups: [
                        { name: "Group1", values: [37, 41] },
                        { name: "Group2", values: [200, 201] },
                    ],
                },
            },
        });
        await waitForDataLoaded(model);
        setCellContent(model, "A1", "=PIVOT(1)");

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:D7")).toEqual({
            A1:"Partner Pivot",  B1: "Group1",       C1: "Group2",       D1: "Total",
            A2: "",              B2: "Probability",  C2: "Probability",  D2: "Probability",
            A3: "xphone",        B3: "10.00",        C3: "",             D3: "10.00",
            A4: "xpad",          B4: "121.00",       C4: "",             D4: "121.00",
            A5: "chair",         B5: "",             C5: "100.00",       D5: "100.00",
            A6: "table",         B6: "",             C6: "50.00",        D6: "50.00",
            A7: "Total",         B7: "131.00",       C7: "150.00",       D7: "281.00",
        });
    });

    test("Custom groups handle None values", async function () {
        Partner._records.push({ id: 202, foo: 12, bar: true, product_id: false, probability: 10 });

        const { model, pivotId } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "GroupedProducts", order: "asc" }],
            rows: [],
            measures: [{ id: "probability:count", fieldName: "probability", aggregator: "count" }],
            customFields: {
                GroupedProducts: {
                    parentField: "product_id",
                    name: "GroupedProducts",
                    groups: [{ name: "Group1", values: [37, 41, 200] }],
                },
            },
        });
        await waitForDataLoaded(model);
        setCellContent(model, "A1", "=PIVOT(1)");

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:E3")).toEqual({
            A1:"Partner Pivot",  B1: "Group1",       C1: "table",        D1: "None",         E1: "Total",
            A2: "",              B2: "Probability",  C2: "Probability",  D2: "Probability",  E2: "Probability",
            A3: "Total",         B3: "5",            C3: "1",            D3: "1",            E3: "7",
        });

        updatePivot(model, pivotId, {
            customFields: {
                GroupedProducts: {
                    parentField: "product_id",
                    name: "GroupedProducts",
                    groups: [{ name: "Group1", values: [37, 41, 200, false] }], // Add false to the group
                },
            },
        });
        await waitForDataLoaded(model);

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:D3")).toEqual({
            A1:"Partner Pivot",  B1: "Group1",       C1: "table",        D1: "Total",
            A2: "",              B2: "Probability",  C2: "Probability",  D2: "Probability",
            A3: "Total",         B3: "6",            C3: "1",            D3: "7",
        });
    });

    test("Can sort custom groups alphabetically", async function () {
        Partner._records.push({ id: 202, foo: 12, bar: true, product_id: false, probability: 10 });

        const { model, pivotId } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "GroupedProducts", order: "asc" }],
            rows: [],
            measures: [{ id: "probability:max", fieldName: "probability", aggregator: "max" }],
            customFields: {
                GroupedProducts: {
                    parentField: "product_id",
                    name: "GroupedProducts",
                    groups: [{ name: "My Group", values: [37, 41] }],
                },
            },
        });
        await waitForDataLoaded(model);
        setCellContent(model, "A1", "=PIVOT(1)");

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:F3")).toEqual({
            A1:"Partner Pivot",  B1: "chair",        C1: "My Group",     D1: "table",        E1: "None",      F1: "Total",
            A2: "",              B2: "Probability",  C2: "Probability",  D2: "Probability",  E2: "Probability",  F2: "Probability",
            A3: "Total",         B3: "100.00",       C3: "95.00",        D3: "50.00",        E3: "10.00",        F3: "100.00",
        });

        updatePivot(model, pivotId, {
            columns: [{ fieldName: "GroupedProducts", order: "desc" }],
        });
        await waitForDataLoaded(model);

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:F3")).toEqual({
            A1:"Partner Pivot",  B1: "None",         C1: "table",        D1: "My Group",     E1: "chair",        F1: "Total",
            A2: "",              B2: "Probability",  C2: "Probability",  D2: "Probability",  E2: "Probability",  F2: "Probability",
            A3: "Total",         B3: "10.00",        C3: "50.00",        D3: "95.00",        E3: "100.00",       F3: "100.00",
        });
    });

    test("Can have a group with all the non-grouped values", async function () {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "GroupedProducts", order: "asc" }],
            rows: [],
            measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
            customFields: {
                GroupedProducts: {
                    parentField: "product_id",
                    name: "GroupedProducts",
                    groups: [
                        { name: "Group1", values: [37, 41] },
                        { name: "Others", values: [], isOtherGroup: true },
                    ],
                },
            },
        });
        await waitForDataLoaded(model);
        setCellContent(model, "A1", "=PIVOT(1)");

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:D3")).toEqual({
            A1:"Partner Pivot",  B1: "Group1",       C1: "Others",       D1: "Total",
            A2: "",              B2: "Probability",  C2: "Probability",  D2: "Probability",
            A3: "Total",         B3: "131.00",       C3: "150.00",       D3: "281.00",
        });
    });

    test("Others group is always sorted at the end", async function () {
        Partner._records.push({ id: 202, foo: 12, bar: true, product_id: false, probability: 10 });

        const { model, pivotId } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "GroupedProducts", order: "asc" }],
            rows: [],
            measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
            customFields: {
                GroupedProducts: {
                    parentField: "product_id",
                    name: "GroupedProducts",
                    groups: [
                        { name: "Group1", values: [37, 41] },
                        { name: "Group2", values: [200, false] },
                        { name: "Others", values: [], isOtherGroup: true },
                    ],
                },
            },
        });
        await waitForDataLoaded(model);
        setCellContent(model, "A1", "=PIVOT(1)");

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:E3")).toEqual({
            A1:"Partner Pivot",  B1: "Group1",       C1: "Group2",       D1: "Others",       E1: "Total",
            A2: "",              B2: "Probability",  C2: "Probability",  D2: "Probability",  E2: "Probability",
            A3: "Total",         B3: "131.00",       C3: "110.00",       D3: "50.00",        E3: "291.00",
        });

        updatePivot(model, pivotId, {
            columns: [{ fieldName: "GroupedProducts", order: "desc" }],
        });
        await waitForDataLoaded(model);

        // prettier-ignore
        expect(getFormattedValueGrid(model, "A1:E3")).toEqual({
            A1:"Partner Pivot",  B1: "Group2",       C1: "Group1",       D1: "Others",       E1: "Total",
            A2: "",              B2: "Probability",  C2: "Probability",  D2: "Probability",  E2: "Probability",
            A3: "Total",         B3: "110.00",       C3: "131.00",       D3: "50.00",        E3: "291.00",
        });
    });
});

describe("Pivot custom groups menu items", () => {
    test("Can add custom groups from the menu items", async function () {
        const { model, pivotId, env } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "product_id" }],
            rows: [],
            measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
        });
        await waitForDataLoaded(model);

        setSelection(model, "C1:E1"); // "xpad", "chair", "table" column headers
        await doMenuAction(cellMenuRegistry, ["pivot_headers_group"], env);
        const definition = model.getters.getPivotCoreDefinition(pivotId);
        expect(definition.customFields).toEqual({
            Product2: {
                parentField: "product_id",
                name: "Product2",
                groups: [{ name: "Group", values: [41, 200, 201] }],
            },
        });
        expect(definition.columns).toEqual([
            { fieldName: "Product2" },
            { fieldName: "product_id" },
        ]);
    });

    test("Grouping a mix of ungrouped an grouped values creates a new group and removes the old one", async function () {
        const { model, pivotId, env } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "product_id" }],
            rows: [],
            measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
            customFields: {
                Product2: {
                    parentField: "product_id",
                    name: "Product2",
                    groups: [{ name: "Group", values: [41, 200, 201] }],
                },
            },
        });
        await waitForDataLoaded(model);

        setSelection(model, "B1:C1"); // "xphone", "xpad" column headers
        await doMenuAction(cellMenuRegistry, ["pivot_headers_group"], env);
        const definition = model.getters.getPivotCoreDefinition(pivotId);
        expect(definition.customFields).toEqual({
            Product2: {
                parentField: "product_id",
                name: "Product2",
                groups: [{ name: "Group", values: [37, 41] }],
            },
        });
        expect(definition.columns).toEqual([
            { fieldName: "Product2" },
            { fieldName: "product_id" },
        ]);
    });

    test("Can merge existing group with other values with menu items", async function () {
        const { model, pivotId, env } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "Product2", order: "asc" }],
            rows: [],
            measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
            customFields: {
                Product2: {
                    parentField: "product_id",
                    name: "Product2",
                    groups: [{ name: "aaGroup", values: [200, 201] }],
                },
            },
        });
        await waitForDataLoaded(model);

        setSelection(model, "B1:C1"); // "aaGroup", "xPad" column headers
        await doMenuAction(cellMenuRegistry, ["pivot_headers_group"], env);
        const definition = model.getters.getPivotCoreDefinition(pivotId);
        expect(definition.customFields).toEqual({
            Product2: {
                parentField: "product_id",
                name: "Product2",
                groups: [{ name: "aaGroup", values: [200, 201, 41] }],
            },
        });
    });

    test("Can remove existing groups with menu items", async function () {
        const { model, pivotId, env } = await createSpreadsheetWithPivot();
        updatePivot(model, pivotId, {
            columns: [{ fieldName: "Product2", order: "asc" }, { fieldName: "product_id" }],
            rows: [],
            measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
            customFields: {
                Product2: {
                    parentField: "product_id",
                    name: "Product2",
                    groups: [
                        { name: "MyGroup", values: [200, 201] },
                        { name: "MyGroup2", values: [37, 41] },
                    ],
                },
            },
        });
        await waitForDataLoaded(model);

        setSelection(model, "B1"); // "MyGroup" column headers
        await doMenuAction(cellMenuRegistry, ["pivot_headers_ungroup"], env);
        await waitForDataLoaded(model);
        let definition = model.getters.getPivotCoreDefinition(pivotId);
        expect(definition.customFields).toEqual({
            Product2: {
                parentField: "product_id",
                name: "Product2",
                groups: [{ name: "MyGroup2", values: [37, 41] }],
            },
        });

        setSelection(model, "C2"); // "xpad" column headers
        await doMenuAction(cellMenuRegistry, ["pivot_headers_ungroup"], env);
        await waitForDataLoaded(model);
        definition = model.getters.getPivotCoreDefinition(pivotId);
        expect(definition.customFields).toEqual({});
        expect(definition.columns).toEqual([{ fieldName: "product_id" }]);
    });
});
