/** @ts-check */
import { describe, expect, test } from "@odoo/hoot";

import { Model } from "@odoo/o-spreadsheet";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import {
    addGlobalFilterWithoutReload,
    setGlobalFilterValueWithoutReload,
} from "@spreadsheet/../tests/helpers/commands";
import { RELATIVE_PERIODS } from "@spreadsheet/global_filters/helpers";

describe.current.tags("headless");
defineSpreadsheetModels();

test("Value of text filter", () => {
    const model = new Model();
    addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "text",
        label: "Text Filter",
    });

    let result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "ilike", strings: "test" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "text",
        label: "Default value is an array",
        defaultValue: { operator: "ilike", strings: ["default value"] },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "ilike", strings: 5 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "ilike", strings: false },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "ilike", strings: [] },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);
});

test("Value of selection filter", () => {
    const model = new Model();
    addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "selection",
        label: "selection Filter",
        resModel: "res.currency",
        selectionField: "position",
    });

    let result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "in", selectionValues: "test" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "selection",
        label: "Default value is an array",
        resModel: "res.currency",
        selectionField: "position",
        defaultValue: { operator: "in", selectionValues: ["default value"] },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "in", selectionValues: 5 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "in", selectionValues: false },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);
});

test("Value of numeric filter", () => {
    const model = new Model();
    addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "numeric",
        label: "Numeric Filter",
        defaultValue: { operator: "=", targetValue: 10 },
    });

    let result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "=", targetValue: false },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "=", targetValue: "value" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "=", targetValue: "5" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "=", targetValue: "" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "numeric",
        label: "Default value is a number",
        defaultValue: { operator: "=", targetValue: 99 },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "2",
    });
    expect(result.isSuccessful).toBe(true);
});

test("Value of date filter", () => {
    const model = new Model();
    addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "date",
        label: "Date Filter",
    });

    let result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: "test",
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "year" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "year", year: 2022 },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: 5,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: false,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "month", month: 5 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "month", year: 2020 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "month", month: 5, year: 2016 },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "quarter", year: 2020 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "quarter", quarter: 3 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "quarter", quarter: 3, year: 2016 },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "year" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { type: "year", year: 2016 },
    });
    expect(result.isSuccessful).toBe(true);

    for (const period of Object.keys(RELATIVE_PERIODS)) {
        result = setGlobalFilterValueWithoutReload(model, {
            id: "1",
            value: { type: "relative", period },
        });
        expect(result.isSuccessful).toBe(true);
    }
});

test("Value of relation filter", () => {
    const model = new Model();
    addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "relation",
        label: "Relation Filter",
    });

    let result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "in", ids: "test" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "in", ids: [1, 2, 3] },
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
    });
    expect(result.isSuccessful).toBe(true);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "in", ids: 5 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "5",
        type: "relation",
        label: "Default value cannot be a boolean",
        defaultValue: { operator: "in", ids: false },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "in", ids: "current_user" }, // TODO check this
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "in", ids: ["1"] },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = setGlobalFilterValueWithoutReload(model, {
        id: "1",
        value: { operator: "in", ids: [] },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);
});
