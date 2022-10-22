/** @odoo-module */

import { nextTick, patchDate } from "@web/../tests/helpers/utils";
import CommandResult from "@spreadsheet/o_spreadsheet/cancelled_reason";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import {
    createModelWithDataSource,
    setupDataSourceEvaluation,
    waitForDataSourcesLoaded,
} from "@spreadsheet/../tests/utils/model";
import { createSpreadsheetWithPivotAndList } from "@spreadsheet/../tests/utils/pivot_list";

import { getCellFormula, getCellValue } from "@spreadsheet/../tests/utils/getters";
import {
    addGlobalFilter,
    editGlobalFilter,
    removeGlobalFilter,
    setCellContent,
    setGlobalFilterValue,
} from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";
import {
    createSpreadsheetWithChart,
    insertChartInSpreadsheet,
} from "@spreadsheet/../tests/utils/chart";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/utils/list";
import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { FILTER_DATE_OPTION } from "@spreadsheet/assets_backend/constants";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import {
    assertDateDomainEqual,
    getDateDomainDurationInDays,
} from "@spreadsheet/../tests/utils/date_domain";
import GlobalFiltersUIPlugin from "@spreadsheet/global_filters/plugins/global_filters_ui_plugin";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";

const { Model, DispatchResult } = spreadsheet;

/**
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").GlobalFilter} GlobalFilter
 *
 * @typedef {Object} FilterPayload
 * @property {GlobalFilter} filter
 */

/** @type FilterPayload */
const LAST_YEAR_FILTER = {
    filter: {
        id: "42",
        type: "date",
        label: "Last Year",
        rangeType: "year",
        defaultValue: { yearOffset: -1 },
    },
};
/** @type FilterPayload */
const LAST_YEAR_LEGACY_FILTER = {
    filter: {
        id: "41",
        type: "date",
        rangeType: "year",
        label: "Legacy Last Year",
        defaultValue: { year: "last_year" },
    },
};
/** @type FilterPayload */
const THIS_YEAR_FILTER = {
    filter: {
        id: "43",
        type: "date",
        label: "This Year",
        rangeType: "year",
        defaultValue: { yearOffset: 0 },
    },
};

const DEFAULT_FIELD_MATCHINGS = {
    1: { chain: "date", type: "date" },
};

QUnit.module("spreadsheet > Global filters model", {}, () => {
    QUnit.test("Can add a global filter", async function (assert) {
        assert.expect(4);

        const { model } = await createSpreadsheetWithPivotAndList();
        assert.equal(model.getters.getGlobalFilters().length, 0);
        await addGlobalFilter(model, LAST_YEAR_FILTER, {
            pivot: DEFAULT_FIELD_MATCHINGS,
        });
        assert.equal(model.getters.getGlobalFilters().length, 1);
        const computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(computedDomain.length, 3);
        assert.equal(computedDomain[0], "&");
    });

    QUnit.test("Can delete a global filter", async function (assert) {
        assert.expect(4);

        const { model } = await createSpreadsheetWithPivotAndList();
        let result = await removeGlobalFilter(model, 1);
        assert.deepEqual(result.reasons, [CommandResult.FilterNotFound]);
        await addGlobalFilter(model, LAST_YEAR_FILTER);
        const gf = model.getters.getGlobalFilters()[0];
        result = await removeGlobalFilter(model, gf.id);
        assert.deepEqual(result, DispatchResult.Success);
        assert.equal(model.getters.getGlobalFilters().length, 0);
        const computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(computedDomain.length, 0);
    });

    QUnit.test("Can edit a global filter", async function (assert) {
        assert.expect(4);

        const { model } = await createSpreadsheetWithPivotAndList();
        const gfDef = { ...THIS_YEAR_FILTER, id: 1 };
        let result = await editGlobalFilter(model, gfDef);
        assert.deepEqual(result.reasons, [CommandResult.FilterNotFound]);
        await addGlobalFilter(model, LAST_YEAR_FILTER);
        const gf = model.getters.getGlobalFilters()[0];
        gfDef.id = gf.id;
        result = await editGlobalFilter(model, gfDef);
        assert.deepEqual(result, DispatchResult.Success);
        assert.equal(model.getters.getGlobalFilters().length, 1);
        assert.deepEqual(model.getters.getGlobalFilters()[0].defaultValue.yearOffset, 0);
    });

    QUnit.test("A global filter with an empty field can be evaluated", async function (assert) {
        const { model } = await createSpreadsheetWithPivotAndList();
        await addGlobalFilter(model, THIS_YEAR_FILTER);
        const domain = model.getters.getPivotComputedDomain(1);
        assert.deepEqual(domain, []);
    });

    QUnit.test("Cannot have duplicated names", async function (assert) {
        assert.expect(6);

        const { model } = await createSpreadsheetWithPivotAndList();
        const filter = { ...THIS_YEAR_FILTER.filter, label: "Hello" };
        await addGlobalFilter(model, { filter });
        assert.equal(model.getters.getGlobalFilters().length, 1);

        // Add filter with same name
        let result = await addGlobalFilter(model, { filter: { ...filter, id: "456" } });
        assert.deepEqual(result.reasons, [CommandResult.DuplicatedFilterLabel]);
        assert.equal(model.getters.getGlobalFilters().length, 1);

        // Edit to set same name as other filter
        await addGlobalFilter(model, {
            filter: { ...filter, id: "789", label: "Other name" },
        });
        assert.equal(model.getters.getGlobalFilters().length, 2);
        result = await editGlobalFilter(model, {
            id: "789",
            filter: { ...filter, label: "Hello" },
        });
        assert.deepEqual(result.reasons, [CommandResult.DuplicatedFilterLabel]);

        // Edit to set same name
        result = await editGlobalFilter(model, {
            id: "789",
            filter: { ...filter, label: "Other name" },
        });
        assert.deepEqual(result, DispatchResult.Success);
    });

    QUnit.test("Can name/rename filters with special characters", async function (assert) {
        assert.expect(5);
        const { model } = await createSpreadsheetWithPivot();
        const filter = Object.assign({}, THIS_YEAR_FILTER.filter, {
            label: "{my} We)ird. |*ab(el []",
        });
        let result = model.dispatch("ADD_GLOBAL_FILTER", { filter });
        assert.deepEqual(result, DispatchResult.Success);
        assert.equal(model.getters.getGlobalFilters().length, 1);

        const filterId = model.getters.getGlobalFilters()[0].id;

        // Edit to set another name with special characters
        result = model.dispatch("EDIT_PIVOT_FILTER", {
            id: filterId,
            filter: Object.assign({}, filter, { label: "+Othe^ we?rd name+$" }),
        });
        assert.deepEqual(result, DispatchResult.Success);

        result = model.dispatch("EDIT_PIVOT_FILTER", {
            id: filterId,
            filter: Object.assign({}, filter, { label: "normal name" }),
        });
        assert.deepEqual(result, DispatchResult.Success);

        result = model.dispatch("EDIT_PIVOT_FILTER", {
            id: filterId,
            filter: Object.assign({}, filter, { label: "?ack +.* to {my} We)ird. |*ab(el []" }),
        });
        assert.deepEqual(result, DispatchResult.Success);
    });

    QUnit.test("Can save a value to an existing global filter", async function (assert) {
        assert.expect(8);

        const { model } = await createSpreadsheetWithPivotAndList();
        await addGlobalFilter(
            model,
            { filter: { ...LAST_YEAR_FILTER.filter, rangeType: "month" } },
            { pivot: DEFAULT_FIELD_MATCHINGS, list: DEFAULT_FIELD_MATCHINGS }
        );
        const gf = model.getters.getGlobalFilters()[0];
        let result = await setGlobalFilterValue(model, {
            id: gf.id,
            value: { period: "february" },
        });
        assert.deepEqual(result, DispatchResult.Success);
        assert.equal(model.getters.getGlobalFilters().length, 1);
        assert.deepEqual(model.getters.getGlobalFilterDefaultValue(gf.id).yearOffset, -1);
        assert.deepEqual(model.getters.getGlobalFilterValue(gf.id).period, "february");
        result = await setGlobalFilterValue(model, {
            id: gf.id,
            value: { period: "march" },
        });
        assert.deepEqual(result, DispatchResult.Success);
        assert.deepEqual(model.getters.getGlobalFilterValue(gf.id).period, "march");
        const computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(computedDomain.length, 3);
        const listDomain = model.getters.getListComputedDomain("1");
        assert.equal(listDomain.length, 3);
    });

    QUnit.test("Domain of simple date filter", async function (assert) {
        patchDate(2022, 6, 14, 0, 0, 0);
        const { model } = await createSpreadsheetWithPivotAndList();
        insertChartInSpreadsheet(model);
        const chartId = model.getters.getOdooChartIds()[0];
        await addGlobalFilter(
            model,
            {
                filter: {
                    ...LAST_YEAR_FILTER.filter,
                },
            },
            {
                pivot: { 1: { chain: "date", type: "date" } },
                list: { 1: { chain: "date", type: "date" } },
                chart: { [chartId]: { chain: "date", type: "date" } },
            }
        );
        const pivotDomain = model.getters.getPivotComputedDomain("1");
        assert.deepEqual(pivotDomain[0], "&");
        assert.deepEqual(pivotDomain[1], ["date", ">=", "2021-01-01"]);
        assert.deepEqual(pivotDomain[2], ["date", "<=", "2021-12-31"]);
        const listDomain = model.getters.getListComputedDomain("1");
        assert.deepEqual(listDomain[0], "&");
        assert.deepEqual(listDomain[1], ["date", ">=", "2021-01-01"]);
        assert.deepEqual(listDomain[2], ["date", "<=", "2021-12-31"]);
        const chartDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
        assert.deepEqual(chartDomain[0], "&");
        assert.deepEqual(chartDomain[1], ["date", ">=", "2021-01-01"]);
        assert.deepEqual(chartDomain[2], ["date", "<=", "2021-12-31"]);
    });

    QUnit.test("Domain of date filter with year offset on pivot field", async function (assert) {
        patchDate(2022, 6, 14, 0, 0, 0);
        const { model } = await createSpreadsheetWithPivot();
        await addGlobalFilter(model, THIS_YEAR_FILTER, {
            pivot: { 1: { chain: "date", type: "date", offset: 1 } },
        });
        const pivotDomain = model.getters.getPivotComputedDomain("1");
        assert.deepEqual(pivotDomain[0], "&");
        assert.deepEqual(pivotDomain[1], ["date", ">=", "2023-01-01"]);
        assert.deepEqual(pivotDomain[2], ["date", "<=", "2023-12-31"]);
    });

    QUnit.test("Domain of date filter with quarter offset on list field", async function (assert) {
        patchDate(2022, 6, 14, 0, 0, 0);
        const { model } = await createSpreadsheetWithList();
        /** @type GlobalFilter */
        const filter = {
            ...THIS_YEAR_FILTER.filter,
            rangeType: "quarter",
            defaultValue: { yearOffset: 0, period: "third_quarter" },
        };
        await addGlobalFilter(
            model,
            { filter },
            {
                list: { 1: { chain: "date", type: "date", offset: 2 } },
            }
        );
        const listDomain = model.getters.getListComputedDomain("1");
        assert.deepEqual(listDomain[0], "&");
        assert.deepEqual(listDomain[1], ["date", ">=", "2023-01-01"]);
        assert.deepEqual(listDomain[2], ["date", "<=", "2023-03-31"]);
    });

    QUnit.test("Domain of date filter with month offset on graph field", async function (assert) {
        patchDate(2022, 6, 14, 0, 0, 0);
        const { model } = await createSpreadsheetWithChart();
        const chartId = model.getters.getOdooChartIds()[0];
        /** @type GlobalFilter */
        const filter = {
            ...THIS_YEAR_FILTER.filter,
            rangeType: "month",
            defaultValue: { yearOffset: 0, period: "july" },
        };
        await addGlobalFilter(
            model,
            { filter },
            {
                chart: { [chartId]: { chain: "date", type: "date", offset: -2 } },
            }
        );
        const chartDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
        assert.deepEqual(chartDomain[0], "&");
        assert.deepEqual(chartDomain[1], ["date", ">=", "2022-05-01"]);
        assert.deepEqual(chartDomain[2], ["date", "<=", "2022-05-31"]);
    });

    QUnit.test("Can import/export filters", async function (assert) {
        const spreadsheetData = migrate({
            sheets: [
                {
                    id: "sheet1",
                    cells: {
                        A1: { content: `=PIVOT("1", "probability")` },
                    },
                },
            ],
            pivots: {
                1: {
                    id: 1,
                    colGroupBys: ["foo"],
                    domain: [],
                    measures: [{ field: "probability", operator: "avg" }],
                    model: "partner",
                    rowGroupBys: ["bar"],
                    context: {},
                    fieldMatching: {
                        41: { type: "date", chain: "date" },
                        42: { type: "date", chain: "date" },
                    },
                },
            },
            lists: {
                1: {
                    id: 1,
                    columns: ["foo", "contact_name"],
                    domain: [],
                    model: "partner",
                    orderBy: [],
                    context: {},
                    fieldMatching: {
                        41: { type: "date", chain: "date" },
                        42: { type: "date", chain: "date" },
                    },
                },
            },
            globalFilters: [LAST_YEAR_LEGACY_FILTER.filter, LAST_YEAR_FILTER.filter],
        });
        const model = await createModelWithDataSource({ spreadsheetData });

        assert.equal(model.getters.getGlobalFilters().length, 2);
        let [filter1, filter2] = model.getters.getGlobalFilters();
        assert.deepEqual(filter1.defaultValue.yearOffset, -1);
        assert.deepEqual(
            model.getters.getGlobalFilterValue(filter1.id).yearOffset,
            -1,
            "it should have applied the default value"
        );
        assert.deepEqual(filter2.defaultValue.yearOffset, -1);
        assert.deepEqual(
            model.getters.getGlobalFilterValue(filter2.id).yearOffset,
            -1,
            "it should have applied the default value"
        );

        let computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(computedDomain.length, 7, "it should have updated the pivot domain");
        let listDomain = model.getters.getListComputedDomain("1");
        assert.equal(listDomain.length, 7, "it should have updated the list domain");

        const newModel = new Model(model.exportData(), {
            external: model.config.external,
        });

        assert.equal(newModel.getters.getGlobalFilters().length, 2);
        [filter1, filter2] = newModel.getters.getGlobalFilters();
        assert.deepEqual(filter1.defaultValue.yearOffset, -1);
        assert.deepEqual(
            newModel.getters.getGlobalFilterValue(filter1.id).yearOffset,
            -1,
            "it should have applied the default value"
        );
        assert.deepEqual(filter2.defaultValue.yearOffset, -1);
        assert.deepEqual(
            newModel.getters.getGlobalFilterValue(filter2.id).yearOffset,
            -1,
            "it should have applied the default value"
        );

        computedDomain = newModel.getters.getPivotComputedDomain("1");
        assert.equal(computedDomain.length, 7, "it should have updated the pivot domain");
        listDomain = newModel.getters.getListComputedDomain("1");
        assert.equal(listDomain.length, 7, "it should have updated the list domain");
    });

    QUnit.test("Relational filter with undefined value", async function (assert) {
        assert.expect(1);

        const { model } = await createSpreadsheetWithPivot();
        await addGlobalFilter(
            model,
            {
                filter: {
                    id: "42",
                    type: "relation",
                    label: "Relation Filter",
                },
            },
            {
                pivot: {
                    1: {
                        field: "foo",
                        type: "char",
                    },
                },
            }
        );
        const [filter] = model.getters.getGlobalFilters();
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: undefined,
        });
        const computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(computedDomain.length, 0, "it should not have updated the pivot domain");
    });

    QUnit.test("Get active filters with multiple filters", async function (assert) {
        assert.expect(2);

        const model = await createModelWithDataSource();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "text",
                label: "Text Filter",
            },
        });
        await addGlobalFilter(model, {
            filter: {
                id: "43",
                type: "date",
                label: "Date Filter",
                rangeType: "quarter",
            },
        });
        await addGlobalFilter(model, {
            filter: {
                id: "44",
                type: "relation",
                label: "Relation Filter",
            },
        });
        const [text] = model.getters.getGlobalFilters();
        assert.equal(model.getters.getActiveFilterCount(), false);
        await setGlobalFilterValue(model, {
            id: text.id,
            value: "Hello",
        });
        assert.equal(model.getters.getActiveFilterCount(), true);
    });

    QUnit.test("Get active filters with text filter enabled", async function (assert) {
        assert.expect(2);

        const model = await createModelWithDataSource();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "text",
                label: "Text Filter",
            },
        });
        const [filter] = model.getters.getGlobalFilters();
        assert.equal(model.getters.getActiveFilterCount(), false);
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: "Hello",
        });
        assert.equal(model.getters.getActiveFilterCount(), true);
    });

    QUnit.test("Get active filters with relation filter enabled", async function (assert) {
        assert.expect(2);

        const model = await createModelWithDataSource();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "relation",
                label: "Relation Filter",
            },
        });
        const [filter] = model.getters.getGlobalFilters();
        assert.equal(model.getters.getActiveFilterCount(), false);
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: [1],
        });
        assert.equal(model.getters.getActiveFilterCount(), true);
    });

    QUnit.test("Get active filters with date filter enabled", async function (assert) {
        assert.expect(4);

        const model = await createModelWithDataSource();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "date",
                label: "Date Filter",
                rangeType: "quarter",
            },
        });
        const [filter] = model.getters.getGlobalFilters();
        assert.equal(model.getters.getActiveFilterCount(), false);
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: {
                yearOffset: 0,
                period: undefined,
            },
        });
        assert.equal(model.getters.getActiveFilterCount(), true);
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: {
                period: "first_quarter",
            },
        });
        assert.equal(model.getters.getActiveFilterCount(), true);
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: {
                yearOffset: 0,
                period: "first_quarter",
            },
        });
        assert.equal(model.getters.getActiveFilterCount(), true);
    });

    QUnit.test("ODOO.FILTER.VALUE text filter", async function (assert) {
        assert.expect(3);

        const model = await createModelWithDataSource();
        setCellContent(model, "A10", `=ODOO.FILTER.VALUE("Text Filter")`);
        await nextTick();
        assert.equal(getCellValue(model, "A10"), "#ERROR");
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "text",
                label: "Text Filter",
            },
        });
        await nextTick();
        assert.equal(getCellValue(model, "A10"), "");
        const [filter] = model.getters.getGlobalFilters();
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: "Hello",
        });
        await nextTick();
        assert.equal(getCellValue(model, "A10"), "Hello");
    });

    QUnit.test("ODOO.FILTER.VALUE date filter", async function (assert) {
        assert.expect(4);

        const model = await createModelWithDataSource();
        setCellContent(model, "A10", `=ODOO.FILTER.VALUE("Date Filter")`);
        await nextTick();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "date",
                label: "Date Filter",
            },
        });
        await nextTick();
        const [filter] = model.getters.getGlobalFilters();
        await setGlobalFilterValue(model, {
            id: filter.id,
            rangeType: "quarter",
            value: {
                yearOffset: 0,
                period: "first_quarter",
            },
        });
        await nextTick();
        assert.equal(getCellValue(model, "A10"), `Q1/${moment().year()}`);
        await setGlobalFilterValue(model, {
            id: filter.id,
            rangeType: "year",
            value: {
                yearOffset: 0,
            },
        });
        await nextTick();
        assert.equal(getCellValue(model, "A10"), `${moment().year()}`);
        await setGlobalFilterValue(model, {
            id: filter.id,
            rangeType: "year",
            value: {
                period: "january",
                yearOffset: 0,
            },
        });
        await nextTick();
        assert.equal(getCellValue(model, "A10"), `01/${moment().year()}`);
        await setGlobalFilterValue(model, {
            id: filter.id,
            rangeType: "year",
            value: {},
        });
        await nextTick();
        assert.equal(getCellValue(model, "A10"), ``);
    });

    QUnit.test("ODOO.FILTER.VALUE relation filter", async function (assert) {
        assert.expect(6);

        const orm = {
            call: async (model, method, args) => {
                const resId = args[0][0];
                assert.step(`name_get_${resId}`);
                return resId === 1 ? [[1, "Jean-Jacques"]] : [[2, "Raoul Grosbedon"]];
            },
        };
        const model = new Model(
            {},
            {
                external: {
                    dataSources: new DataSources({ ...orm, silent: orm }),
                    env: { services: { orm } },
                },
            }
        );
        setupDataSourceEvaluation(model);
        setCellContent(model, "A10", `=ODOO.FILTER.VALUE("Relation Filter")`);
        await nextTick();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "relation",
                label: "Relation Filter",
                modelName: "partner",
            },
        });
        await nextTick();
        const [filter] = model.getters.getGlobalFilters();

        // One record; displayNames not defined => rpc
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: [1],
        });
        await nextTick();
        assert.equal(getCellValue(model, "A10"), "Jean-Jacques");

        // Two records; displayNames defined => no rpc
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: [1, 2],
            displayNames: ["Jean-Jacques", "Raoul Grosbedon"],
        });
        await nextTick();
        assert.equal(getCellValue(model, "A10"), "Jean-Jacques, Raoul Grosbedon");

        // another record; displayNames not defined => rpc
        await setGlobalFilterValue(model, {
            id: filter.id,
            value: [2],
        });
        await nextTick();
        assert.equal(getCellValue(model, "A10"), "Raoul Grosbedon");
        assert.verifySteps(["name_get_1", "name_get_2"]);
    });

    QUnit.test(
        "ODOO.FILTER.VALUE formulas are updated when filter label is changed",
        async function (assert) {
            assert.expect(1);

            const model = await createModelWithDataSource();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "date",
                    label: "Cuillère",
                },
            });
            setCellContent(
                model,
                "A10",
                `=ODOO.FILTER.VALUE("Cuillère") & ODOO.FILTER.VALUE( "Cuillère" )`
            );
            const [filter] = model.getters.getGlobalFilters();
            const newFilter = {
                type: "date",
                label: "Interprete",
            };
            await editGlobalFilter(model, { id: filter.id, filter: newFilter });
            assert.equal(
                getCellFormula(model, "A10"),
                `=ODOO.FILTER.VALUE("Interprete") & ODOO.FILTER.VALUE("Interprete")`
            );
        }
    );

    QUnit.test("Exporting data does not remove value from model", async function (assert) {
        assert.expect(2);

        const model = await createModelWithDataSource();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "text",
                label: "Cuillère",
            },
        });
        await setGlobalFilterValue(model, {
            id: "42",
            value: "Hello export bug",
        });
        const [filter] = model.getters.getGlobalFilters();
        assert.equal(model.getters.getGlobalFilterValue(filter.id), "Hello export bug");
        model.exportData();
        assert.equal(model.getters.getGlobalFilterValue(filter.id), "Hello export bug");
    });

    QUnit.test("Can undo-redo a ADD_GLOBAL_FILTER", async function (assert) {
        assert.expect(3);

        const model = await createModelWithDataSource();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "text",
                label: "Cuillère",
            },
        });
        assert.equal(model.getters.getGlobalFilters().length, 1);
        model.dispatch("REQUEST_UNDO");
        assert.equal(model.getters.getGlobalFilters().length, 0);
        model.dispatch("REQUEST_REDO");
        assert.equal(model.getters.getGlobalFilters().length, 1);
    });

    QUnit.test("Can undo-redo a REMOVE_GLOBAL_FILTER", async function (assert) {
        assert.expect(3);

        const model = await createModelWithDataSource();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "text",
                label: "Cuillère",
            },
        });
        await removeGlobalFilter(model, "42");
        assert.equal(model.getters.getGlobalFilters().length, 0);
        model.dispatch("REQUEST_UNDO");
        assert.equal(model.getters.getGlobalFilters().length, 1);
        model.dispatch("REQUEST_REDO");
        assert.equal(model.getters.getGlobalFilters().length, 0);
    });

    QUnit.test("Can undo-redo a EDIT_GLOBAL_FILTER", async function (assert) {
        assert.expect(3);

        const model = await createModelWithDataSource();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "text",
                label: "Cuillère",
            },
        });
        await editGlobalFilter(model, {
            id: "42",
            filter: {
                id: "42",
                type: "text",
                label: "Arthouuuuuur",
            },
        });
        assert.equal(model.getters.getGlobalFilters()[0].label, "Arthouuuuuur");
        model.dispatch("REQUEST_UNDO");
        assert.equal(model.getters.getGlobalFilters()[0].label, "Cuillère");
        model.dispatch("REQUEST_REDO");
        assert.equal(model.getters.getGlobalFilters()[0].label, "Arthouuuuuur");
    });

    QUnit.test("pivot headers won't change when adding a filter ", async function (assert) {
        assert.expect(6);
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.equal(getCellValue(model, "A3"), "xphone");
        assert.equal(getCellValue(model, "A4"), "xpad");
        await addGlobalFilter(
            model,
            {
                filter: {
                    id: "42",
                    type: "relation",
                    label: "Relation Filter",
                    modelName: "product",
                    defaultValue: [41],
                },
            },
            { pivot: { 1: { chain: "product_id", type: "many2one" } } }
        );
        assert.equal(getCellValue(model, "A3"), "xphone");
        assert.equal(getCellValue(model, "B3"), "");
        assert.equal(getCellValue(model, "A4"), "xpad");
        assert.equal(getCellValue(model, "B4"), "121");
    });

    QUnit.test(
        "load data only once if filter is not active (without default value)",
        async function (assert) {
            const spreadsheetData = {
                sheets: [
                    {
                        id: "sheet1",
                        cells: {
                            A1: { content: `=ODOO.PIVOT("1", "probability")` },
                        },
                    },
                ],
                pivots: {
                    1: {
                        id: 1,
                        colGroupBys: ["foo"],
                        domain: [],
                        measures: [{ field: "probability", operator: "avg" }],
                        model: "partner",
                        rowGroupBys: ["bar"],
                        context: {},
                    },
                },
                globalFilters: [
                    {
                        id: "filterId",
                        type: "date",
                        label: "my filter",
                        defaultValue: {},
                        rangeType: "year",
                    },
                ],
            };
            const model = await createModelWithDataSource({
                spreadsheetData,
                mockRPC: function (route, { model, method, kwargs }) {
                    if (model === "partner" && method === "read_group") {
                        assert.step(`${model}/${method}`);
                    }
                },
            });
            await waitForDataSourcesLoaded(model);
            assert.verifySteps([
                "partner/read_group",
                "partner/read_group",
                "partner/read_group",
                "partner/read_group",
            ]);
            assert.equal(getCellValue(model, "A1"), 131);
        }
    );

    QUnit.test(
        "load data only once if filter is active (with a default value)",
        async function (assert) {
            const spreadsheetData = {
                sheets: [
                    {
                        id: "sheet1",
                        cells: {
                            A1: { content: `=ODOO.PIVOT("1", "probability")` },
                        },
                    },
                ],
                pivots: {
                    1: {
                        id: 1,
                        colGroupBys: ["foo"],
                        domain: [],
                        measures: [{ field: "probability", operator: "avg" }],
                        model: "partner",
                        rowGroupBys: ["bar"],
                        context: {},
                        fieldMatching: { filterId: { chain: "date", type: "date" } },
                    },
                },
                globalFilters: [
                    {
                        id: "filterId",
                        type: "date",
                        label: "my filter",
                        defaultValue: { yearOffset: 0 },
                        rangeType: "year",
                    },
                ],
            };
            const model = await createModelWithDataSource({
                spreadsheetData,
                mockRPC: function (route, { model, method, kwargs }) {
                    if (model === "partner" && method === "read_group") {
                        assert.step(`${model}/${method}`);
                    }
                },
            });
            await waitForDataSourcesLoaded(model);
            assert.verifySteps(["partner/read_group"]);
            assert.equal(getCellValue(model, "A1"), "");
        }
    );

    QUnit.test("don't reload data if an empty filter is added", async function (assert) {
        const spreadsheetData = {
            sheets: [
                {
                    id: "sheet1",
                    cells: {
                        A1: { content: `=ODOO.PIVOT("1", "probability")` },
                    },
                },
            ],
            pivots: {
                1: {
                    id: 1,
                    colGroupBys: ["foo"],
                    domain: [],
                    measures: [{ field: "probability", operator: "avg" }],
                    model: "partner",
                    rowGroupBys: ["bar"],
                    context: {},
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: function (route, { model, method, kwargs }) {
                if (model === "partner" && method === "read_group") {
                    assert.step(`${model}/${method}`);
                }
            },
        });
        await waitForDataSourcesLoaded(model);
        assert.verifySteps([
            "partner/read_group",
            "partner/read_group",
            "partner/read_group",
            "partner/read_group",
        ]);
        assert.strictEqual(getCellValue(model, "A1"), 131);
        model.dispatch("ADD_GLOBAL_FILTER", {
            filter: {
                id: "42",
                type: "date",
                rangeType: "month",
                label: "This month",
                defaultValue: {}, // no default value!
            },
        });
        assert.strictEqual(getCellValue(model, "A1"), 131);
        assert.verifySteps([]);
    });

    QUnit.test(
        "don't load data if a filter is added but the data is not needed",
        async function (assert) {
            const spreadsheetData = {
                sheets: [
                    {
                        id: "sheet1",
                    },
                    {
                        id: "sheet2",
                        cells: {
                            A1: { content: `=ODOO.PIVOT("1", "probability")` },
                        },
                    },
                ],
                pivots: {
                    1: {
                        id: 1,
                        colGroupBys: ["foo"],
                        domain: [],
                        measures: [{ field: "probability", operator: "avg" }],
                        model: "partner",
                        rowGroupBys: ["bar"],
                        context: {},
                        fieldMatching: {},
                    },
                },
            };
            const model = await createModelWithDataSource({
                spreadsheetData,
                mockRPC: function (route, { model, method, kwargs }) {
                    if (model === "partner" && method === "read_group") {
                        assert.step(`${model}/${method}`);
                    }
                },
            });
            assert.verifySteps([]);
            model.dispatch("ADD_GLOBAL_FILTER", {
                filter: {
                    id: "42",
                    type: "date",
                    rangeType: "month",
                    label: "This month",
                    defaultValue: { period: "january" },
                },
                pivot: {
                    1: { chain: "date", type: "date" },
                },
            });
            assert.verifySteps([]);
            model.dispatch("ACTIVATE_SHEET", { sheetIdFrom: "sheet1", sheetIdTo: "sheet2" });
            assert.equal(getCellValue(model, "A1"), "Loading...");
            await nextTick();
            assert.equal(getCellValue(model, "A1"), "");
            assert.verifySteps(["partner/read_group"]);
        }
    );

    QUnit.test(
        "don't load data if a filter is activated but the data is not needed",
        async function (assert) {
            const spreadsheetData = {
                sheets: [
                    {
                        id: "sheet1",
                    },
                    {
                        id: "sheet2",
                        cells: {
                            A1: { content: `=ODOO.PIVOT("1", "probability")` },
                        },
                    },
                ],
                pivots: {
                    1: {
                        id: 1,
                        colGroupBys: ["foo"],
                        domain: [],
                        measures: [{ field: "probability", operator: "avg" }],
                        model: "partner",
                        rowGroupBys: ["bar"],
                        context: {},
                        fieldMatching: { filterId: { chain: "date", type: "date" } },
                    },
                },
                globalFilters: [
                    {
                        id: "filterId",
                        type: "date",
                        label: "my filter",
                        defaultValue: {},
                        rangeType: "year",
                    },
                ],
            };
            const model = await createModelWithDataSource({
                spreadsheetData,
                mockRPC: function (route, { model, method, kwargs }) {
                    if (model === "partner" && method === "read_group") {
                        assert.step(`${model}/${method}`);
                    }
                },
            });
            assert.verifySteps([]);
            model.dispatch("SET_GLOBAL_FILTER_VALUE", {
                id: "filterId",
                value: { yearOffset: 0 },
            });

            assert.verifySteps([]);
            model.dispatch("ACTIVATE_SHEET", { sheetIdFrom: "sheet1", sheetIdTo: "sheet2" });
            assert.equal(getCellValue(model, "A1"), "Loading...");
            await nextTick();
            assert.equal(getCellValue(model, "A1"), "");
            assert.verifySteps(["partner/read_group"]);
        }
    );

    QUnit.test("Default value defines value", async function (assert) {
        assert.expect(1);

        const { model } = await createSpreadsheetWithPivot();
        const label = "This year";
        const defaultValue = "value";
        await addGlobalFilter(model, {
            filter: { id: "42", type: "text", label, defaultValue },
        });
        const [filter] = model.getters.getGlobalFilters();
        assert.equal(model.getters.getGlobalFilterValue(filter.id), defaultValue);
    });

    QUnit.test("Default value defines value at model loading", async function (assert) {
        assert.expect(1);
        const label = "This year";
        const defaultValue = "value";
        const model = new Model({
            globalFilters: [{ type: "text", label, defaultValue, fields: {}, id: "1" }],
        });
        const [filter] = model.getters.getGlobalFilters();
        assert.equal(model.getters.getGlobalFilterValue(filter.id), defaultValue);
    });

    QUnit.test("filter display value of year filter is a string", async function (assert) {
        const { model } = await createSpreadsheetWithPivotAndList();
        await addGlobalFilter(model, THIS_YEAR_FILTER);
        const [filter] = model.getters.getGlobalFilters();
        assert.strictEqual(
            model.getters.getFilterDisplayValue(filter.label),
            String(new Date().getFullYear())
        );
    });

    QUnit.test("Export global filters for excel", async function (assert) {
        const { model } = await createSpreadsheetWithPivotAndList();
        await addGlobalFilter(model, THIS_YEAR_FILTER);
        const [filter] = model.getters.getGlobalFilters();
        const filterPlugin = model["handlers"].find(
            (handler) => handler instanceof GlobalFiltersUIPlugin
        );
        const exportData = { styles: [], sheets: [] };
        filterPlugin.exportForExcel(exportData);
        const filterSheet = exportData.sheets[0];
        assert.ok(filterSheet, "A sheet to export global filters was created");
        assert.equal(filterSheet.cells["A1"].content, "Filter");
        assert.equal(filterSheet.cells["A2"].content, filter.label);
        assert.equal(filterSheet.cells["B1"].content, "Value");
        assert.equal(
            filterSheet.cells["B2"].content,
            model.getters.getFilterDisplayValue(filter.label)
        );
    });

    QUnit.test("Date filter automatic default value for years filter", async function (assert) {
        const label = "This year";
        const { model } = await createSpreadsheetWithPivot();
        await addGlobalFilter(model, {
            filter: {
                id: "1",
                type: "date",
                label,
                defaultsToCurrentPeriod: true,
                rangeType: "year",
            },
        });
        assert.deepEqual(model.getters.getGlobalFilterValue("1"), {
            yearOffset: 0,
        });
    });

    QUnit.test("Date filter automatic default value for month filter", async function (assert) {
        patchDate(2022, 2, 10, 0, 0, 0);
        const label = "This month";
        const { model } = await createSpreadsheetWithPivot();
        await addGlobalFilter(model, {
            filter: {
                id: "1",
                type: "date",
                label,
                defaultsToCurrentPeriod: true,
                rangeType: "month",
            },
        });
        assert.deepEqual(model.getters.getGlobalFilterValue("1"), {
            yearOffset: 0,
            period: "march",
        });
    });

    QUnit.test("Date filter automatic default value for quarter filter", async function (assert) {
        patchDate(2022, 11, 10, 0, 0, 0);
        const label = "This quarter";
        const { model } = await createSpreadsheetWithPivot();
        await addGlobalFilter(model, {
            filter: {
                id: "1",
                type: "date",
                label,
                defaultsToCurrentPeriod: true,
                rangeType: "quarter",
            },
        });
        assert.deepEqual(model.getters.getGlobalFilterValue("1"), {
            yearOffset: 0,
            period: FILTER_DATE_OPTION.quarter[3],
        });
    });

    QUnit.test("Date filter automatic default value at model loading", async function (assert) {
        const label = "This year";
        const model = new Model({
            globalFilters: [
                {
                    type: "date",
                    label,
                    defaultsToCurrentPeriod: true,
                    defaultValue: {},
                    fields: {},
                    id: "1",
                    rangeType: "year",
                },
            ],
        });
        assert.deepEqual(model.getters.getGlobalFilterValue("1"), {
            yearOffset: 0,
        });
    });

    QUnit.test("Relative date filter at model loading", async function (assert) {
        const label = "Last Month";
        const defaultValue = RELATIVE_DATE_RANGE_TYPES[1].type;
        const model = new Model({
            globalFilters: [
                { type: "date", rangeType: "relative", label, defaultValue, fields: {}, id: "1" },
            ],
        });
        assert.equal(model.getters.getGlobalFilterValue("1"), defaultValue);
    });

    QUnit.test("Relative date filter display value", async function (assert) {
        patchDate(2022, 4, 16, 0, 0, 0);
        const label = "Last Month";
        const defaultValue = RELATIVE_DATE_RANGE_TYPES[1].type;
        const { model } = await createSpreadsheetWithPivot();
        await addGlobalFilter(model, {
            filter: {
                id: "42",
                type: "date",
                label,
                defaultValue,
                rangeType: "relative",
            },
        });
        assert.equal(
            model.getters.getFilterDisplayValue(label),
            RELATIVE_DATE_RANGE_TYPES[1].description
        );
    });

    QUnit.test("Relative date filter domain value", async function (assert) {
        patchDate(2022, 4, 16, 0, 0, 0);
        const label = "Last Month";
        const { model } = await createSpreadsheetWithPivot();
        /**@type GlobalFilter */
        const filter = {
            id: "42",
            type: "date",
            label,
            defaultValue: "last_week",
            rangeType: "relative",
        };
        await addGlobalFilter(model, { filter }, { pivot: { 1: { chain: "date", type: "date" } } });
        let computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 7);
        assertDateDomainEqual(assert, "date", "2022-05-09", "2022-05-15", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_month" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 30);
        assertDateDomainEqual(assert, "date", "2022-04-16", "2022-05-15", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_three_months" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 90);
        assertDateDomainEqual(assert, "date", "2022-02-15", "2022-05-15", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_six_months" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 180);
        assertDateDomainEqual(assert, "date", "2021-11-17", "2022-05-15", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_year" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 365);
        assertDateDomainEqual(assert, "date", "2021-05-16", "2022-05-15", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_three_years" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 3 * 365);
        assertDateDomainEqual(assert, "date", "2019-05-17", "2022-05-15", computedDomain);
    });

    QUnit.test("Relative date filter with offset domain value", async function (assert) {
        patchDate(2022, 4, 16, 0, 0, 0);
        const label = "Last Month";
        const { model } = await createSpreadsheetWithPivot();
        /**@type GlobalFilter */
        const filter = {
            id: "42",
            type: "date",
            label,
            defaultValue: "last_week",
            rangeType: "relative",
        };
        await addGlobalFilter(
            model,
            { filter },
            { pivot: { 1: { chain: "date", type: "date", offset: -1 } } }
        );
        let computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 7);
        assertDateDomainEqual(assert, "date", "2022-05-02", "2022-05-08", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_month" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 30);
        assertDateDomainEqual(assert, "date", "2022-03-17", "2022-04-15", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_three_months" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 90);
        assertDateDomainEqual(assert, "date", "2021-11-17", "2022-02-14", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_six_months" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 180);
        assertDateDomainEqual(assert, "date", "2021-05-21", "2021-11-16", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_year" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 365);
        assertDateDomainEqual(assert, "date", "2020-05-16", "2021-05-15", computedDomain);

        await setGlobalFilterValue(model, { id: "42", value: "last_three_years" });
        computedDomain = model.getters.getPivotComputedDomain("1");
        assert.equal(getDateDomainDurationInDays(computedDomain), 3 * 365);
        assertDateDomainEqual(assert, "date", "2016-05-17", "2019-05-16", computedDomain);
    });

    QUnit.test(
        "Can set a value to a relation filter from the SET_MANY_GLOBAL_FILTER_VALUE command",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "relation",
                },
            });
            model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
                filters: [{ filterId: "42", value: [31] }],
            });
            assert.deepEqual(model.getters.getGlobalFilterValue("42"), [31]);
            model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters: [{ filterId: "42" }] });
            assert.deepEqual(model.getters.getGlobalFilterValue("42"), []);
        }
    );

    QUnit.test(
        "Can set a value to a date filter from the SET_MANY_GLOBAL_FILTER_VALUE command",
        async function (assert) {
            patchDate(2022, 6, 14, 0, 0, 0);
            const { model } = await createSpreadsheetWithPivot();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "date",
                    rangeType: "month",
                },
            });
            const newValue = { yearOffset: -6, period: "may" };
            model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
                filters: [{ filterId: "42", value: newValue }],
            });
            assert.deepEqual(model.getters.getGlobalFilterValue("42"), newValue);
            model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters: [{ filterId: "42" }] });
            assert.deepEqual(model.getters.getGlobalFilterValue("42"), {
                yearOffset: undefined,
                preventAutomaticValue: true,
            });
        }
    );

    QUnit.test(
        "getFiltersMatchingPivot return correctly matching filter according to cell formula",
        async function (assert) {
            patchDate(2022, 6, 14, 0, 0, 0);
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                    <field name="date" interval="month" type="col"/>
                </pivot>`,
            });
            await addGlobalFilter(
                model,
                {
                    filter: {
                        id: "42",
                        type: "relation",
                        label: "relational filter",
                    },
                },
                {
                    pivot: { 1: { chain: "product_id", type: "many2one" } },
                }
            );
            await addGlobalFilter(
                model,
                {
                    filter: {
                        id: "43",
                        type: "date",
                        label: "date filter 1",
                        rangeType: "month",
                    },
                },
                {
                    pivot: { 1: { chain: "date", type: "date" } },
                }
            );
            await addGlobalFilter(
                model,
                {
                    filter: {
                        id: "44",
                        type: "date",
                        label: "date filter 2",
                        rangeType: "year",
                    },
                },
                {
                    pivot: { 1: { chain: "date", type: "date" } },
                }
            );
            const relationalFilters1 = model.getters.getFiltersMatchingPivot(
                '=ODOO.PIVOT.HEADER(1,"product_id",37)'
            );
            assert.deepEqual(relationalFilters1, [{ filterId: "42", value: [37] }]);
            const relationalFilters2 = model.getters.getFiltersMatchingPivot(
                '=ODOO.PIVOT.HEADER(1,"product_id","41")'
            );
            assert.deepEqual(relationalFilters2, [{ filterId: "42", value: [41] }]);
            const dateFilters1 = model.getters.getFiltersMatchingPivot(
                '=ODOO.PIVOT.HEADER(1,"date:month","08/2016")'
            );
            assert.deepEqual(dateFilters1, [
                { filterId: "43", value: { yearOffset: -6, period: "august" } },
            ]);
            const dateFilters2 = model.getters.getFiltersMatchingPivot(
                '=ODOO.PIVOT.HEADER(1,"date:year","2016")'
            );
            assert.deepEqual(dateFilters2, [{ filterId: "44", value: { yearOffset: -6 } }]);
        }
    );

    QUnit.test(
        "getFiltersMatchingPivot return an empty array if there is no pivot formula",
        async function (assert) {
            const model = await createModelWithDataSource();
            const result = model.getters.getFiltersMatchingPivot("=1");
            assert.deepEqual(result, []);
        }
    );

    QUnit.test(
        "getFiltersMatchingPivot return correctly matching filter according to cell formula with multi-levels grouping",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                    <field name="date" interval="month" type="row"/>
                </pivot>`,
            });
            await addGlobalFilter(
                model,
                {
                    filter: {
                        id: "42",
                        type: "relation",
                        label: "relational filter",
                    },
                },
                {
                    pivot: { 1: { chain: "product_id", type: "many2one" } },
                }
            );
            await addGlobalFilter(
                model,
                {
                    filter: {
                        id: "43",
                        type: "date",
                        label: "date filter 1",
                        rangeType: "month",
                    },
                },
                {
                    pivot: { 1: { chain: "product_id", type: "many2one" } },
                }
            );
            const filters = model.getters.getFiltersMatchingPivot(
                '=ODOO.PIVOT.HEADER(1,"date:month","08/2016","product_id","41")'
            );
            assert.deepEqual(filters, [{ filterId: "42", value: [41] }]);
        }
    );

    QUnit.test(
        "getFiltersMatchingPivot return correctly matching filter according to cell formula with __count and positional argument",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="__count" type="measure"/>
                </pivot>`,
            });
            setCellContent(model, "B3", '=ODOO.PIVOT(1, "__count", "#product_id", 1)');
            await addGlobalFilter(
                model,
                {
                    filter: {
                        id: "42",
                        type: "relation",
                        defaultValue: [],
                    },
                },
                { pivot: { 1: { chain: "product_id", type: "many2one" } } }
            );
            const filters = model.getters.getFiltersMatchingPivot(getCellFormula(model, "B3"));
            assert.deepEqual(filters, [
                {
                    filterId: "42",
                    value: [37],
                },
            ]);
        }
    );

    QUnit.test(
        "getFiltersMatchingPivot return correctly matching filter according to cell formula with positional argument",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            setCellContent(model, "B3", '=ODOO.PIVOT(1, "probability", "#product_id", 1)');
            await addGlobalFilter(
                model,
                {
                    filter: {
                        id: "42",
                        type: "relation",
                        defaultValue: [],
                    },
                },
                { pivot: { 1: { chain: "product_id", type: "many2one" } } }
            );
            const filters = model.getters.getFiltersMatchingPivot(getCellFormula(model, "B3"));
            assert.deepEqual(filters, [
                {
                    filterId: "42",
                    value: [37],
                },
            ]);
        }
    );

    QUnit.test(
        "getFiltersMatchingPivot return correctly matching filter when there is a filter with no field defined",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "relation",
                    defaultValue: [],
                },
            });
            const filters = model.getters.getFiltersMatchingPivot(getCellFormula(model, "B3"));
            assert.deepEqual(filters, []);
        }
    );

    QUnit.test(
        "getFiltersMatchingPivot return empty filter for cell formula without any argument",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            setCellContent(model, "B3", '=ODOO.PIVOT(1, "probability")');
            await addGlobalFilter(
                model,
                {
                    filter: {
                        id: "42",
                        type: "relation",
                        defaultValue: [],
                    },
                },
                { pivot: { 1: { chain: "product_id", type: "many2one" } } }
            );
            const filters = model.getters.getFiltersMatchingPivot(getCellFormula(model, "B3"));
            assert.deepEqual(filters, []);
        }
    );

    QUnit.test(
        "getFiltersMatchingPivot return empty filter when no records is related to the pivot cell",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            setCellContent(model, "B3", '=ODOO.PIVOT(1, "probability", "#product_id", 1)');
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "relation",
                    defaultValue: [1],
                    pivotFields: { 1: { field: "product_id", type: "many2one" } },
                },
            });
            const filters = model.getters.getFiltersMatchingPivot(getCellFormula(model, "B3"));
            assert.deepEqual(filters, []);
        }
    );

    QUnit.test("field matching is removed when pivot is deleted", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        await addGlobalFilter(model, LAST_YEAR_FILTER, { pivot: DEFAULT_FIELD_MATCHINGS });
        const [pivotId] = model.getters.getPivotIds();
        const [filter] = model.getters.getGlobalFilters();
        const matching = {
            chain: "date",
            type: "date",
        };
        assert.deepEqual(model.getters.getPivotFieldMatching(pivotId, filter.id), matching);
        model.dispatch("REMOVE_PIVOT", { pivotId });
        assert.throws(
            () => model.getters.getPivotFieldMatching(pivotId, filter.id),
            "Pivot does not exist"
        );
        model.dispatch("REQUEST_UNDO");
        assert.deepEqual(model.getters.getPivotFieldMatching(pivotId, filter.id), matching);
        model.dispatch("REQUEST_REDO");
        assert.throws(
            () => model.getters.getPivotFieldMatching(pivotId, filter.id),
            "Pivot does not exist"
        );
    });

    QUnit.test("field matching is removed when list is deleted", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        await addGlobalFilter(model, LAST_YEAR_FILTER, { list: DEFAULT_FIELD_MATCHINGS });
        const [listId] = model.getters.getListIds();
        const [filter] = model.getters.getGlobalFilters();
        const matching = {
            chain: "date",
            type: "date",
        };
        assert.deepEqual(model.getters.getListFieldMatching(listId, filter.id), matching);
        model.dispatch("REMOVE_ODOO_LIST", { listId });
        assert.throws(
            () => model.getters.getListFieldMatching(listId, filter.id),
            "List does not exist"
        );
        model.dispatch("REQUEST_UNDO");
        assert.deepEqual(model.getters.getListFieldMatching(listId, filter.id), matching);
        model.dispatch("REQUEST_REDO");
        assert.throws(
            () => model.getters.getListFieldMatching(listId, filter.id),
            "List does not exist"
        );
    });

    QUnit.test("field matching is removed when an Odoo chart is deleted", async function (assert) {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
        const sheetId = model.getters.getActiveSheetId();
        const [chartId] = model.getters.getChartIds(sheetId);
        await addGlobalFilter(model, LAST_YEAR_FILTER, {
            chart: { [chartId]: { chain: "date", type: "date" } },
        });
        const [filter] = model.getters.getGlobalFilters();
        const matching = {
            chain: "date",
            type: "date",
        };
        assert.deepEqual(model.getters.getOdooChartFieldMatching(chartId, filter.id), matching);
        model.dispatch("DELETE_FIGURE", { id: chartId, sheetId });
        assert.throws(
            () => model.getters.getOdooChartFieldMatching(chartId, filter.id),
            "Chart does not exist"
        );
        model.dispatch("REQUEST_UNDO");
        assert.deepEqual(model.getters.getOdooChartFieldMatching(chartId, filter.id), matching);
        model.dispatch("REQUEST_REDO");
        assert.throws(
            () => model.getters.getOdooChartFieldMatching(chartId, filter.id),
            "Chart does not exist"
        );
    });

    QUnit.test(
        "getFiltersMatchingPivot return correctly matching filter with the 'measure' special field",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
                </pivot>`,
            });
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    label: "fake",
                    type: "relation",
                    defaultValue: [],
                },
            });
            const filters = model.getters.getFiltersMatchingPivot(getCellFormula(model, "B2"));
            assert.deepEqual(filters, []);
        }
    );

    QUnit.test("Reject date filters with invalid field Matchings", async (assert) => {
        const { model } = await createSpreadsheetWithPivotAndList();
        insertChartInSpreadsheet(model);
        const chartId = model.getters.getOdooChartIds()[0];

        const filter = (label) => ({
            filter: {
                id: "42",
                label,
                type: "date",
                defaultValue: {},
            },
        });
        const resultPivot = await addGlobalFilter(model, filter("fake1"), {
            pivot: { 1: { offset: -2 } },
        });
        assert.deepEqual(resultPivot.reasons, [CommandResult.InvalidFieldMatch]);
        const resultList = await addGlobalFilter(model, filter("fake2"), {
            list: { 1: { offset: -2 } },
        });
        assert.deepEqual(resultList.reasons, [CommandResult.InvalidFieldMatch]);
        const resultChart = await addGlobalFilter(model, filter("fake3"), {
            chart: { [chartId]: { offset: -2 } },
        });
        assert.deepEqual(resultChart.reasons, [CommandResult.InvalidFieldMatch]);
    });

    QUnit.test("Can create a relative date filter with an empty default value", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        const filter = {
            filter: {
                id: "42",
                label: "test",
                type: "date",
                defaultValue: {},
                rangeType: "relative",
            },
        };
        const result = await addGlobalFilter(model, filter);
        assert.ok(result.isSuccessful);
    });
});
