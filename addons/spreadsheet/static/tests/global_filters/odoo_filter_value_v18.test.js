/** @ts-check */
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import {
    defineSpreadsheetModels,
} from "@spreadsheet/../tests/helpers/data";
import {
    createModelWithDataSource,
} from "@spreadsheet/../tests/helpers/model";

import {
    addGlobalFilter,
    setCellContent,
    setGlobalFilterValue,
} from "@spreadsheet/../tests/helpers/commands";
import {
    getCellValue,
    getEvaluatedCell,
} from "@spreadsheet/../tests/helpers/getters";

describe.current.tags("headless");
defineSpreadsheetModels();

const { DateTime } = luxon;

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 *
 */


test("ODOO.FILTER.VALUE.V18 text filter", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A10", `=ODOO.FILTER.VALUE.V18("Text Filter")`);
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("#ERROR");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("");
    const [filter] = model.getters.getGlobalFilters();
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "ilike", strings: ["Hello"] },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("Hello");
});

test("ODOO.FILTER.VALUE.V18 empty date filter does't spill", async function () {
    mockDate("2022-03-10 00:00:00");
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A10", `=ODOO.FILTER.VALUE.V18("Date Filter")`);
    setCellContent(model, "B10", "something");
    await animationFrame();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    expect(getCellValue(model, "A10")).toBe("");
});

test("ODOO.FILTER.VALUE.V18 date filter", async function () {
    mockDate("2022-03-10 00:00:00");
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A10", `=ODOO.FILTER.VALUE.V18("Date Filter")`);
    await animationFrame();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await animationFrame();
    const [filter] = model.getters.getGlobalFilters();
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: {
            type: "quarter",
            year: 2022,
            quarter: 1,
        },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe(`Q1/${DateTime.now().year}`);
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: {
            type: "year",
            year: 2022,
        },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe(`${DateTime.now().year}`);
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: {
            type: "month",
            year: 2022,
            month: 1,
        },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe(`01/${DateTime.now().year}`);
    await setGlobalFilterValue(model, {
        id: filter.id,
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe(``);
});

test("ODOO.FILTER.VALUE.V18 date from/to without values", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    setCellContent(model, "A1", `=ODOO.FILTER.VALUE.V18("Date Filter")`);
    expect(getEvaluatedCell(model, "A1").value).toBe("");
    expect(getEvaluatedCell(model, "B1").value).toBe(null);
});

test("ODOO.FILTER.VALUE.V18 date from/to with only from defined", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.FILTER.VALUE.V18("Date Filter")`);
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: {
            type: "range",
            from: "2020-01-01",
        },
    });
    expect(getEvaluatedCell(model, "A1").value).toBe(43831);
    expect(getEvaluatedCell(model, "A1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("1/1/2020");
    expect(getEvaluatedCell(model, "B1").value).toBe("");
});

test("ODOO.FILTER.VALUE.V18 date from/to with only to defined", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.FILTER.VALUE.V18("Date Filter")`);
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: {
            type: "range",
            to: "2020-01-01",
        },
    });
    expect(getEvaluatedCell(model, "A1").value).toBe("");
    expect(getEvaluatedCell(model, "B1").value).toBe(43831);
    expect(getEvaluatedCell(model, "B1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("1/1/2020");
});

test("ODOO.FILTER.VALUE.V18 date from/to with from and to defined", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.FILTER.VALUE.V18("Date Filter")`);
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: {
            type: "range",
            from: "2020-01-01",
            to: "2021-01-01",
        },
    });
    expect(getEvaluatedCell(model, "A1").value).toBe(43831);
    expect(getEvaluatedCell(model, "A1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("1/1/2020");
    expect(getEvaluatedCell(model, "B1").value).toBe(44197);
    expect(getEvaluatedCell(model, "B1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("1/1/2021");
});

test("ODOO.FILTER.VALUE.V18 relation filter", async function () {
    const { model } = await createModelWithDataSource({
        mockRPC: function (route, { method, args }) {
            if (method === "web_search_read") {
                const resIds = args[0][0][2];
                const names = {
                    1: "Jean-Jacques",
                    2: "Raoul Grosbedon",
                };
                expect.step(`read_${resIds}`);
                return { records: resIds.map((resId) => ({ id: resId, display_name: names[resId] })) };
            }
        },
    });
    setCellContent(model, "A10", `=ODOO.FILTER.VALUE.V18("Relation Filter")`);
    await animationFrame();
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "Relation Filter",
        modelName: "partner",
    });
    await animationFrame();
    const [filter] = model.getters.getGlobalFilters();
    expect.verifySteps([]);
    // One record; displayNames not defined => rpc
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "in", ids: [1] },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("Jean-Jacques");

    // Two records; displayNames defined => no rpc
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "in", ids: [1, 2] },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("Jean-Jacques, Raoul Grosbedon");

    // another record; displayNames not defined => rpc
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "in", ids: [2] },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("Raoul Grosbedon");
    expect.verifySteps(["read_1", "read_1,2", "read_2"]);
});

test("ODOO.FILTER.VALUE.V18 with escaped quotes in the filter label", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: 'my "special" filter',
        defaultValue: { operator: "ilike", strings: ["Jean-Jacques"] },
    });
    setCellContent(model, "A1", '=ODOO.FILTER.VALUE.V18("my \\"special\\" filter")');
    expect(getCellValue(model, "A1")).toBe("Jean-Jacques");
});
