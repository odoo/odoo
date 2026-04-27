import {
    defineDocumentSpreadsheetModels,
    DocumentsDocument,
    getBasicData,
    getBasicServerData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { createSpreadsheetFromListView } from "@documents_spreadsheet/../tests/helpers/list_helpers";
import { createSpreadsheetFromPivotView } from "@documents_spreadsheet/../tests/helpers/pivot_helpers";
import { createSpreadsheet } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { queryAllTexts, queryAllValues, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { helpers } from "@odoo/o-spreadsheet";
import { insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import {
    addGlobalFilter,
    editGlobalFilter,
    selectCell,
    setCellContent,
} from "@spreadsheet/../tests/helpers/commands";
import { getBasicPivotArch, IrModel, Partner } from "@spreadsheet/../tests/helpers/data";
import { assertDateDomainEqual } from "@spreadsheet/../tests/helpers/date_domain";
import { getCellValue } from "@spreadsheet/../tests/helpers/getters";
import {
    LAST_YEAR_GLOBAL_FILTER,
    THIS_YEAR_GLOBAL_FILTER,
} from "@spreadsheet/../tests/helpers/global_filter";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/helpers/list";
import { insertPivotInSpreadsheet } from "@spreadsheet/../tests/helpers/pivot";
import { toRangeData } from "@spreadsheet/../tests/helpers/zones";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import * as domainHelpers from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineModels,
    fields,
    makeServerError,
    models,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { monthsOptions } from "@spreadsheet/assets_backend/constants";
import { user } from "@web/core/user";
import { QUARTER_OPTIONS } from "@web/search/utils/dates";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

const { toZone } = helpers;
const monthsOptionsIds = monthsOptions.map((option) => option.id);
const quarterOptionsIds = Object.values(QUARTER_OPTIONS).map((option) => option.id);

/**
 * @typedef {import("@spreadsheet").FixedPeriodDateGlobalFilter} FixedPeriodDateGlobalFilter
 */

let target;

const FILTER_CREATION_SELECTORS = {
    text: ".o_global_filter_new_text",
    date: ".o_global_filter_new_time",
    relation: ".o_global_filter_new_relation",
};

class Vehicle extends models.Model {
    _name = "vehicle";
}

class Computer extends models.Model {
    _name = "computer";
}

async function openGlobalFilterSidePanel() {
    await contains(".o_topbar_filter_icon").click();
}

/**
 * @param {"text" | "date" | "relation"} type
 */
async function clickCreateFilter(type) {
    await contains(FILTER_CREATION_SELECTORS[type]).click();
}

async function selectModelForRelation(relation) {
    await contains('.o_side_panel_related_model input[type="text"]').click();
    await contains(`.o_model_selector_${relation}`).click();
}

async function selectFieldMatching(fieldName, fieldMatching = target) {
    // skipVisibilityCheck because the section is collapsible, which we don't care about in the tests
    await contains(fieldMatching.querySelector(".o_model_field_selector"), {
        visible: false,
    }).click();
    // We use `target` here because the popover is not in fieldMatching
    await contains(`.o_model_field_selector_popover_item[data-name='${fieldName}'] button`).click();
}

async function saveGlobalFilter() {
    await contains(".o_global_filter_save").click();
}

async function cancelGlobalFilterEdition() {
    await contains(".o_global_filter_cancel").click();
}

async function editGlobalFilterLabel(label) {
    await contains(".o_global_filter_label").edit(label);
}

async function editGlobalFilterDefaultValue(defaultValue) {
    await contains(".o-global-filter-text-value").edit(defaultValue);
}

async function selectYear(yearString) {
    const input = target.querySelector("input.o_datetime_input");
    // open the YearPicker
    await contains(input).click();
    // Change input value
    await contains(input).edit(yearString);
    await animationFrame();
}

beforeEach(() => {
    target = getFixture();
});

test("Simple display", async function () {
    await createSpreadsheetFromPivotView();
    expect(".o_spreadsheet_global_filters_side_panel").toHaveCount(0);

    await openGlobalFilterSidePanel();
    expect(".o_spreadsheet_global_filters_side_panel").toHaveCount(1);

    const buttons = target.querySelectorAll(".o_spreadsheet_global_filters_side_panel .o-button");
    expect(buttons.length).toBe(3);
    expect(buttons[0]).toHaveClass("o_global_filter_new_time");
    expect(buttons[1]).toHaveClass("o_global_filter_new_relation");
    expect(buttons[2]).toHaveClass("o_global_filter_new_text");
});

test("Display with an existing 'Date' global filter", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    const label = "This year";
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        rangeType: "fixedPeriod",
        label,
        defaultValue: {},
    });
    await openGlobalFilterSidePanel();
    const sections = target.querySelectorAll(".o_spreadsheet_global_filters_side_panel .o-section");
    expect(sections.length).toBe(2);
    const labelElement = sections[0].querySelector(".o_side_panel_filter_label");
    expect(labelElement).toHaveText(label);

    await contains(sections[0].querySelector(".o_side_panel_filter_icon.fa-cog")).click();
    expect(".o_spreadsheet_filter_editor_side_panel").toHaveCount(1);
    expect(".o_global_filter_label").toHaveValue(label);
});

test("Pivot display name is displayed in field matching", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    model.dispatch("RENAME_PIVOT", { pivotId, name: "Hello" });
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        rangeType: "fixedPeriod",
        label: "This year",
        defaultValue: {},
    });

    await openGlobalFilterSidePanel();
    await contains(".o_side_panel_filter_icon.fa-cog").click();
    const name = target.querySelector(".o_spreadsheet_field_matching .fw-medium").innerText;
    expect(name).toBe("Hello");
});

test("List display name is displayed in field matching", async function () {
    const { model } = await createSpreadsheetFromListView();
    const [listId] = model.getters.getListIds();
    model.dispatch("RENAME_ODOO_LIST", { listId, name: "Hello" });
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        rangeType: "fixedPeriod",
        label: "This year",
        defaultValue: {},
    });

    await openGlobalFilterSidePanel();
    await contains(".o_side_panel_filter_icon.fa-cog").click();
    const name = target.querySelector(".o_spreadsheet_field_matching .fw-medium").innerText;
    expect(name).toBe("Hello");
});

test("Create a new text global filter", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("text");
    await editGlobalFilterLabel("My Label");
    await editGlobalFilterDefaultValue("Default Value");
    await selectFieldMatching("name");
    expect(".o_filter_field_offset").toHaveCount(0, {
        message: "No offset for text filter",
    });
    await saveGlobalFilter();

    expect(".o_spreadsheet_global_filters_side_panel").toHaveCount(1);

    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("My Label");
    expect(globalFilter.defaultValue).toBe("Default Value");
    expect(globalFilter.rangeOfAllowedValues).toBe(undefined);
});

test("Create a new text global filter with a range", async function () {
    const { model } = await createSpreadsheet();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("text");
    await editGlobalFilterLabel("My Label");
    await contains(".restrict_to_range input[type=checkbox]").click();
    selectCell(model, "B1");
    await animationFrame();
    expect(".o-selection-input input").toHaveValue("B1");
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.rangeOfAllowedValues.zone).toEqual(toZone("B1"));
});

test("Create a new text global filter with a default value from a range", async function () {
    const { model } = await createSpreadsheet();
    setCellContent(model, "B1", "hello");
    await openGlobalFilterSidePanel();
    await clickCreateFilter("text");
    await editGlobalFilterLabel("My Label");
    await contains(".restrict_to_range input[type=checkbox]").click();
    selectCell(model, "B1");
    await animationFrame();
    await animationFrame(); // SelectionInput component needs an extra tick to update
    expect(queryAllTexts("select option")).toEqual(["Choose a value...", "hello"]);
    await contains("select").select("hello");
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.defaultValue).toBe("hello");
});

test("Create a new text global filter, set a default value ,then restrict values to range", async function () {
    const { model } = await createSpreadsheet();
    setCellContent(model, "B1", "hello");
    await openGlobalFilterSidePanel();
    await clickCreateFilter("text");
    await editGlobalFilterLabel("My Label");
    await editGlobalFilterDefaultValue("hi");
    await contains(".restrict_to_range input[type=checkbox]").click();
    selectCell(model, "B1");
    await animationFrame();
    await animationFrame(); // SelectionInput component needs an extra tick to update
    expect(queryAllTexts("select option")).toEqual(["Choose a value...", "hello", "hi"]);
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.defaultValue).toBe("hi");
});

test("edit a text global filter with a default value not from the range", async function () {
    const { model } = await createSpreadsheet();
    const sheetId = model.getters.getActiveSheetId();
    addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "a filter",
        defaultValue: "Hi",
        rangeOfAllowedValues: toRangeData(sheetId, "B2"),
    });
    setCellContent(model, "B2", "hello"); // the range does not contain the default value
    await animationFrame();
    await openGlobalFilterSidePanel();
    // open edition panel
    await contains(".pivot_filter_input .fa-cog").click();
    expect("select").toHaveValue("Hi");
    expect(queryAllTexts("select option")).toEqual(["Choose a value...", "hello", "Hi"]);
    await saveGlobalFilter(); // save without changing anything
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.defaultValue).toBe("Hi");
});

test("check range text filter but don't select any range", async function () {
    const { model } = await createSpreadsheet();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("text");
    await editGlobalFilterLabel("My Label");
    await contains(".restrict_to_range input[type=checkbox]").click();
    await animationFrame();
    expect(".o-selection-input input").toHaveValue("");
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.rangeOfAllowedValues).toBe(undefined);
});

test("check and uncheck range for text filter", async function () {
    const { model } = await createSpreadsheet();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("text");
    await editGlobalFilterLabel("My Label");
    await contains(".restrict_to_range input[type=checkbox]").click();
    selectCell(model, "B1");
    await animationFrame();
    expect(".o-selection-input input").toHaveValue("B1");
    await contains(".restrict_to_range input[type=checkbox]").click();
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.rangeOfAllowedValues).toBe(undefined);
});

test("Create a new relational global filter", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("product");
    expect(".o_filter_field_offset").toHaveCount(0, {
        message: "No offset for relational filter",
    });
    await saveGlobalFilter();
    expect(".o_spreadsheet_global_filters_side_panel").toHaveCount(1);
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("Product");
    expect(globalFilter.defaultValue).toEqual([]);
    expect(model.getters.getPivotFieldMatching(pivotId, globalFilter.id)).toEqual({
        chain: "product_id",
        type: "many2one",
    });
});

test("Can select ID in relation filter", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                    <pivot string="Partners">
                        <field name="foo" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            },
        },
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("partner");
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(model.getters.getPivotFieldMatching(pivotId, globalFilter.id)).toEqual({
        chain: "id",
        type: "integer",
    });
});

test("Cannot select ID in date filter", async function () {
    await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                    <pivot string="Partners">
                        <field name="foo" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            },
        },
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("date");
    await contains(".o_model_field_selector_value").click();
    expect(target.querySelectorAll("[data-name='id']").length).toBe(0);
});

test("Cannot select ID in text filter", async function () {
    await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                    <pivot string="Partners">
                        <field name="foo" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            },
        },
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("text");
    await contains(".o_model_field_selector_value").click();
    expect(target.querySelectorAll("[data-name='id']").length).toBe(0);
});

test("Create a new many2many relational global filter", async function () {
    defineModels([Vehicle]);
    const serverData = getBasicServerData();
    const vehicleField = fields.Many2many({
        relation: "vehicle",
        searchable: true,
        string: "Vehicle",
    });
    Partner._fields.vehicle_ids = vehicleField;
    serverData.models["ir.model"] = {
        records: [{ id: 34, name: "Vehicle", model: "vehicle" }],
    };
    const { model, pivotId } = await createSpreadsheetFromPivotView({ serverData });

    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("vehicle");
    expect(".o_model_field_selector_value").toHaveText("Vehicle");
    await saveGlobalFilter();

    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("Vehicle");
    expect(globalFilter.defaultValue).toEqual([]);
    expect(model.getters.getPivotFieldMatching(pivotId, globalFilter.id)).toEqual({
        chain: "vehicle_ids",
        type: "many2many",
    });
});

test("Filter component is visible even without data source", async function () {
    await createSpreadsheet();
    expect(".o_topbar_filter_icon").toHaveCount(1);
});

test("Cannot create a relation filter without data source", async function () {
    await createSpreadsheet();
    await openGlobalFilterSidePanel();
    expect(".o_global_filter_new_time").toHaveCount(1);
    expect(".o_global_filter_new_relation").toHaveCount(0);
    expect(".o_global_filter_new_text").toHaveCount(1);
});

test("Can create a relation filter with at least a data source", async function () {
    await createSpreadsheetFromPivotView();
    await openGlobalFilterSidePanel();
    expect(".o_global_filter_new_time").toHaveCount(1);
    expect(".o_global_filter_new_relation").toHaveCount(1);
    expect(".o_global_filter_new_text").toHaveCount(1);
});

test("Panel has collapsible section with field matching in new filters", async function () {
    await createSpreadsheetFromPivotView();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("date");
    await animationFrame();
    const collapsible = target.querySelector(".o-sidePanel .collapsible_section");
    expect(".o_spreadsheet_field_matching").toHaveCount(1);
    expect(collapsible).toHaveClass("show");

    await contains(".o-sidePanel .collapsor").click();
    expect(collapsible).not.toHaveClass("show");
});

test("Collapsible section with field matching is collapsed for existing filter", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await openGlobalFilterSidePanel();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        pivot: { [pivotId]: { type: "date", chain: "date" } },
    });
    await animationFrame();

    await contains(".o_side_panel_filter_icon.fa-cog").click();
    const collapsible = target.querySelector(".o-sidePanel .collapsible_section");
    expect(collapsible).not.toHaveClass("show");
});

test("Creating a date filter without a data source does not display Field Matching", async function () {
    await createSpreadsheet();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("date");
    expect(".o-sidePanel .collapsible_section").toHaveCount(0);
});

test("open relational global filter panel then go to pivot on sheet 2", async function () {
    const spreadsheetData = {
        version: 16,
        sheets: [
            { id: "sheet1" },
            {
                id: "sheet2",
                cells: { A1: { content: `=PIVOT.VALUE("1", "probability")` } },
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
    const serverData = getBasicServerData();
    serverData.models["documents.document"].records = [
        DocumentsDocument._records[0], // res_company.document_spreadsheet_folder_id
        {
            id: 45,
            spreadsheet_data: JSON.stringify(spreadsheetData),
            name: "Spreadsheet",
            handler: "spreadsheet",
        },
    ];
    const { model } = await createSpreadsheet({
        serverData,
        spreadsheetId: 45,
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("product");
    const fieldMatching = target.querySelector(".o_spreadsheet_field_matching div");
    expect(fieldMatching).toHaveText("partner (Pivot #1)", {
        message: "model display name is loaded",
    });
    await saveGlobalFilter();
    model.dispatch("ACTIVATE_SHEET", { sheetIdFrom: "sheet1", sheetIdTo: "sheet2" });
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe(131);
});

test("Prevent selection of a Field Matching before the Related model", async function () {
    await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                                <pivot string="Partners">
                                    <field name="foo" type="col"/>
                                    <field name="product_id" type="row"/>
                                    <field name="probability" type="measure"/>
                                </pivot>`,
            },
        },
        mockRPC: async function (route, args) {
            if (args.method === "search_read" && args.model === "ir.model") {
                return [{ name: "Product", model: "product" }];
            }
        },
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    expect(".o_spreadsheet_field_matching").toHaveCount(0);
    await selectModelForRelation("product");
    expect(".o_spreadsheet_field_matching").toHaveCount(1);
});

test("Display with an existing 'Relation' global filter", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    const pivotId2 = "PIVOT#2";
    await insertPivotInSpreadsheet(model, pivotId2, { arch: getBasicPivotArch() });
    const label = "MyFoo";
    const filter = {
        id: "42",
        type: "relation",
        modelName: "product",
        label,
        defaultValue: [],
    };
    await addGlobalFilter(model, filter, {
        pivot: {
            [pivotId]: { type: "many2one", chain: "product_id" }, // first pivotId
            [pivotId2]: { type: "many2one", chain: "product_id" }, // second pivotId
        },
    });
    await openGlobalFilterSidePanel();
    const sections = target.querySelectorAll(".o_spreadsheet_global_filters_side_panel .o-section");
    expect(sections.length).toBe(2);
    const labelElement = sections[0].querySelector(".o_side_panel_filter_label");
    expect(labelElement).toHaveText(label);
    await contains(sections[0].querySelector(".o_side_panel_filter_icon.fa-cog")).click();
    expect(".o_spreadsheet_filter_editor_side_panel").toHaveCount(1);
    expect(".o_global_filter_label").toHaveValue(label);
    expect(`.o_side_panel_related_model input`).toHaveValue("Product");
    const fieldsMatchingElements = target.querySelectorAll(
        "span.o_model_field_selector_chain_part"
    );
    expect(fieldsMatchingElements.length).toBe(2);
    expect(fieldsMatchingElements[0]).toHaveText("Product");
    expect(fieldsMatchingElements[1]).toHaveText("Product");
});

test("Display name for 'Relation' global filter values can be updated correctly", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    const label = "MyFoo";
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        modelName: "product",
        label,
        defaultValue: [],
    });
    await openGlobalFilterSidePanel();
    await contains(".o-autocomplete--input.o_input").click();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);
    const item1 = target.querySelector(".o-autocomplete--dropdown-item");
    await contains(item1).click();
    expect(model.getters.getFilterDisplayValue(label)[0][0].value).toBe(item1.innerText);
});

test("Only related models can be selected", async function () {
    defineModels([Vehicle, Computer]);
    const data = getBasicData();
    data["ir.model"].records = [
        ...IrModel._records,
        {
            id: 36,
            name: "Apple",
            model: "apple",
        },
        {
            id: 35,
            name: "Document",
            model: "documents.document",
        },
        {
            id: 34,
            name: "Vehicle",
            model: "vehicle",
        },
        {
            id: 33,
            name: "Computer",
            model: "computer",
        },
    ];
    const document = fields.Many2one({ relation: "documents.document", string: "Document" });
    const vehicle_ids = fields.Many2many({ relation: "vehicle", string: "Vehicle" });
    const computer_ids = fields.One2many({ relation: "computer", string: "Computer" });
    Partner._fields = { ...Partner._fields, document, vehicle_ids, computer_ids };

    await createSpreadsheetFromPivotView({
        serverData: {
            models: data,
            views: {
                "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await contains(".o_side_panel_related_model input").click();
    const [model1, model2, model3, model4, model5, model6, model7] = target.querySelectorAll(
        ".o-autocomplete--dropdown-item a"
    );
    expect(model1).toHaveText("Apple");
    expect(model2).toHaveText("Computer");
    expect(model3).toHaveText("Document");
    expect(model4).toHaveText("Partner");
    expect(model5).toHaveText("Product");
    expect(model6).toHaveText("Users");
    expect(model7).toHaveText("Vehicle");
});

test("Edit an existing global filter", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    const label = "This year";
    const defaultValue = "value";
    await addGlobalFilter(model, { id: "42", type: "text", label, defaultValue });
    await openGlobalFilterSidePanel();
    await contains(".o_side_panel_filter_icon.fa-cog").click();
    expect(".o-sidePanel").toHaveCount(1);
    expect(".o_global_filter_label").toHaveValue(label);
    expect(".o-global-filter-text-value").toHaveValue(defaultValue);
    await editGlobalFilterLabel("New Label");
    await selectFieldMatching("name");
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("New Label");
});

test("Trying to duplicate a filter label will trigger a toaster", async function () {
    const uniqueFilterName = "UNIQUE_FILTER";
    const { model } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                            <pivot>
                                <field name="bar" type="col"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: uniqueFilterName,
        modelName: "product",
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("text");
    await editGlobalFilterLabel(uniqueFilterName);
    await editGlobalFilterDefaultValue("Default Value");
    await selectFieldMatching("name");
    await saveGlobalFilter();
    expect(".o_notification:has(.o_notification_bar.bg-danger)").toHaveText("Duplicated Label");
});

test("Create a new relational global filter with a pivot", async function () {
    const spreadsheetData = {
        version: 16,
        pivots: {
            "PIVOT#1": {
                colGroupBys: ["foo"],
                domain: [],
                measures: [{ field: "probability", operator: "avg" }],
                model: "partner",
                rowGroupBys: ["bar"],
                context: {},
            },
        },
    };
    const serverData = getBasicServerData();
    serverData.models["documents.document"].records = [
        DocumentsDocument._records[0], // res_company.document_spreadsheet_folder_id
        {
            id: 45,
            spreadsheet_data: JSON.stringify(spreadsheetData),
            name: "Spreadsheet",
            handler: "spreadsheet",
        },
    ];
    const { model } = await createSpreadsheet({
        serverData,
        spreadsheetId: 45,
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("product");
    await saveGlobalFilter();
    expect(target.querySelectorAll(".o_spreadsheet_global_filters_side_panel").length).toBe(1);
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("Product");
    expect(globalFilter.defaultValue).toEqual([]);
    expect(model.getters.getPivotFieldMatching("PIVOT#1", globalFilter.id)).toEqual({
        chain: "product_id",
        type: "many2one",
    });
});

test("Create a new relational global filter with a chart", async function () {
    const { model } = await createSpreadsheet();
    insertChartInSpreadsheet(model);
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("product");
    await saveGlobalFilter();
    const [chartId] = model.getters.getOdooChartIds();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("Product");
    expect(globalFilter.defaultValue).toEqual([]);
    expect(model.getters.getOdooChartFieldMatching(chartId, globalFilter.id)).toEqual({
        chain: "product_id",
        type: "many2one",
    });
});

test("Create a new relational global filter with a domain", async function () {
    onRpc("/web/domain/validate", () => true);
    const { model } = await createSpreadsheetFromPivotView();
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("product");
    expect(".o_edit_domain").toHaveCount(0);
    await contains(".o-checkbox:contains(Restrict values with a domain)").click();
    await contains(".o_edit_domain").click();
    await domainHelpers.addNewRule();
    await contains(".modal-footer .btn-primary").click();
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.domainOfAllowedValues).toEqual([["id", "=", 1]]);
});

test("Create a new relational global filter of users will shows the checkbox", async function () {
    const serverData = getBasicServerData();
    const { model } = await createSpreadsheetFromPivotView({ serverData });
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("res\\.users");
    const defaultUserOption = document.querySelector("#user_automatic_filter");
    expect(defaultUserOption).not.toBe(null);
    expect(defaultUserOption).not.toBeChecked();
    await contains(defaultUserOption).click();
    expect(defaultUserOption).toBeChecked();
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    const id = globalFilter.id;
    const userId = model.getters.getGlobalFilterValue(id);
    expect([user.userId]).toEqual(userId);
    expect(globalFilter.defaultValue).toBe("current_user");
    expect(globalFilter.label).toBe("Users");
});

test("Create a new relational global filter with a parent/child model", async function () {
    const serverData = getBasicServerData();
    const { model } = await createSpreadsheetFromPivotView({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "has_searchable_parent_relation" && args.args[0] === "product") {
                return true;
            }
        },
    });
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("product");
    const checkbox = queryFirst(".o-checkbox:contains(Include children)");
    expect(checkbox).toHaveText("Include children");
    expect(checkbox.querySelector("input").checked).toBe(true);
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.includeChildren).toBe(true);
});

test("edit a relational global filter to uncheck a parent/child model", async function () {
    const serverData = getBasicServerData();
    const { model } = await createSpreadsheetFromPivotView({ serverData });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        modelName: "product",
        label: "Relation Filter",
        includeChildren: true,
        defaultValue: [],
    });
    await animationFrame();
    await openGlobalFilterSidePanel();
    await contains(".fa-cog").click();
    const checkbox = queryFirst(".o-checkbox:contains(Include children)");
    expect(checkbox.querySelector("input").checked).toBe(true);
    await contains(checkbox).click();
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.includeChildren).toBe(false);
});

test("switching relational model displays the children checkbox or not", async function () {
    const serverData = getBasicServerData();
    serverData.models["ir.model"].records = [
        ...IrModel._records,
        {
            id: 999,
            name: "Currency",
            model: "res.currency",
        },
    ];
    await createSpreadsheetFromPivotView({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "has_searchable_parent_relation" && args.args[0] === "product") {
                return true;
            }
        },
    });
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    expect(".o-checkbox:contains(Include children)").toHaveCount(0);

    await selectModelForRelation("res\\.currency");
    expect(".o-checkbox:contains(Include children)").toHaveCount(0);

    await selectModelForRelation("product");
    expect(".o-checkbox:contains(Include children)").toHaveCount(1);
    expect(queryFirst(".o-checkbox:contains(Include children) input").checked).toBe(true);

    await selectModelForRelation("res\\.currency");
    expect(".o-checkbox:contains(Include children)").toHaveCount(0);
});

test("Create a new relational global filter with a list snapshot", async function () {
    const spreadsheetData = {
        lists: {
            1: {
                id: 1,
                columns: ["foo", "contact_name"],
                domain: [],
                model: "partner",
                orderBy: [],
                context: {},
                fieldMatching: {},
            },
        },
    };
    const serverData = getBasicServerData();
    serverData.models["documents.document"].records = [
        DocumentsDocument._records[0], // res_company.document_spreadsheet_folder_id
        {
            id: 45,
            spreadsheet_data: JSON.stringify(spreadsheetData),
            name: "Spreadsheet",
            handler: "spreadsheet",
        },
    ];
    const { model } = await createSpreadsheet({
        serverData,
        spreadsheetId: 45,
    });
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("product");
    await saveGlobalFilter();
    expect(target.querySelectorAll(".o_spreadsheet_global_filters_side_panel").length).toBe(1);
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("Product");
    expect(globalFilter.defaultValue).toEqual([]);
    expect(model.getters.getListFieldMatching("1", globalFilter.id)).toEqual({
        chain: "product_id",
        type: "many2one",
    });
});

test("Create a new date filter", async function () {
    mockDate("2022-07-10 00:00:00");
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    insertChartInSpreadsheet(model);
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("date");
    expect(".o-sidePanel").toHaveCount(1);
    await editGlobalFilterLabel("My Label");

    const range = target.querySelector(".o-filter-range-type");
    await contains(range).select("fixedPeriod");

    await contains("input[name=date_automatic_filter]").click();

    const pivotFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[0];
    const listFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[1];
    const graphFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[2];

    await selectFieldMatching("date", pivotFieldMatching);
    await selectFieldMatching("date", listFieldMatching);
    await selectFieldMatching("date", graphFieldMatching);

    await saveGlobalFilter();

    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("My Label");
    expect(globalFilter.rangeType).toBe("fixedPeriod");
    expect(globalFilter.type).toBe("date");
    const pivotDomain = model.getters.getPivotComputedDomain(pivotId);
    assertDateDomainEqual("date", "2022-07-01", "2022-07-31", pivotDomain);
    expect(model.getters.getPivotFieldMatching(pivotId, globalFilter.id).offset).toBe(0);
    model.getters.getPivotFieldMatching(pivotId, globalFilter.id);
    const listDomain = model.getters.getListComputedDomain("1");
    assertDateDomainEqual("date", "2022-07-01", "2022-07-31", listDomain);
    expect(model.getters.getListFieldMatching("1", globalFilter.id).offset).toBe(0);
    const chartId = model.getters.getOdooChartIds()[0];
    const graphDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
    assertDateDomainEqual("date", "2022-07-01", "2022-07-31", graphDomain);
    expect(model.getters.getOdooChartFieldMatching(chartId, globalFilter.id).offset).toBe(0);
});

test("Create a new date filter with period offsets", async function () {
    mockDate("2022-07-14 00:00:00");
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    insertChartInSpreadsheet(model);
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("date");
    await editGlobalFilterLabel("My Label");

    const range = target.querySelector(".o-filter-range-type");
    await contains(range).select("fixedPeriod");

    await contains("input[name=date_automatic_filter]").click();

    const pivotFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[0];
    const listFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[1];
    const chartFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[2];

    // pivot
    await selectFieldMatching("date", pivotFieldMatching);
    await contains(pivotFieldMatching.querySelector("select")).select("-1");

    //list
    await selectFieldMatching("date", listFieldMatching);

    // chart
    await selectFieldMatching("date", chartFieldMatching);
    await contains(chartFieldMatching.querySelector("select")).select("-2");

    await saveGlobalFilter();

    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("My Label");
    expect(globalFilter.rangeType).toBe("fixedPeriod");
    expect(globalFilter.type).toBe("date");
    const pivotDomain = model.getters.getPivotComputedDomain(pivotId);

    expect(model.getters.getPivotFieldMatching(pivotId, globalFilter.id).offset).toBe(-1);
    assertDateDomainEqual("date", "2022-06-01", "2022-06-30", pivotDomain);
    const listDomain = model.getters.getListComputedDomain("1");
    expect(model.getters.getListFieldMatching("1", globalFilter.id).offset).toBe(0);
    assertDateDomainEqual("date", "2022-07-01", "2022-07-31", listDomain);
    const chartId = model.getters.getOdooChartIds()[0];
    const chartDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
    expect(model.getters.getOdooChartFieldMatching(chartId, globalFilter.id).offset).toBe(-2);
    assertDateDomainEqual("date", "2022-05-01", "2022-05-31", chartDomain);
});

test("Cannot a new date filter with period offsets without setting the field chain first", async () => {
    await createSpreadsheetFromPivotView();
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("date");
    await editGlobalFilterLabel("My Label");

    const pivotFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[0];
    expect(".o_filter_field_offset select.o-input").toHaveProperty("disabled", true);

    // pivot
    await selectFieldMatching("date", pivotFieldMatching);
    expect(".o_filter_field_offset select.o-input").toHaveProperty("disabled", false);
});

test("Create a new relative date filter with an empty default value", async () => {
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    insertChartInSpreadsheet(model);
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("date");
    await editGlobalFilterLabel("My Label");

    const range = target.querySelector(".o-filter-range-type");
    await contains(range).select("relative");

    const relativeSelection = target.querySelector("select.o_relative_date_selection");
    const values = relativeSelection.querySelectorAll("option");
    expect([...values].map((val) => val.value)).toEqual([
        "",
        ...RELATIVE_DATE_RANGE_TYPES.map((item) => item.type),
    ]);
    await contains(relativeSelection).select("");

    const pivotFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[0];
    const listFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[1];
    const graphFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[2];

    await selectFieldMatching("date", pivotFieldMatching);
    await selectFieldMatching("date", listFieldMatching);
    await selectFieldMatching("date", graphFieldMatching);

    await contains(graphFieldMatching.querySelector("select")).select("-2");

    await saveGlobalFilter();

    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("My Label");
    expect(globalFilter.defaultValue).toBe("");
    expect(globalFilter.rangeType).toBe("relative");
    expect(globalFilter.type).toBe("date");
    const pivotDomain = model.getters.getPivotComputedDomain(pivotId);
    expect(pivotDomain).toEqual([]);
    const listDomain = model.getters.getListComputedDomain("1");
    expect(listDomain).toEqual([]);
    const chartId = model.getters.getOdooChartIds()[0];
    const chartDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
    expect(chartDomain).toEqual([]);
});

test("Create a new relative date filter", async function () {
    mockDate("2022-07-14 00:00:00");
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    insertChartInSpreadsheet(model);
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("date");
    await editGlobalFilterLabel("My Label");

    const range = target.querySelector(".o-filter-range-type");
    await contains(range).select("relative");

    const relativeSelection = target.querySelector("select.o_relative_date_selection");
    const values = relativeSelection.querySelectorAll("option");
    expect([...values].map((val) => val.value)).toEqual([
        "",
        ...RELATIVE_DATE_RANGE_TYPES.map((item) => item.type),
    ]);
    await contains(relativeSelection).select("last_month");

    const pivotFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[0];
    const listFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[1];
    const graphFieldMatching = target.querySelectorAll(".o_spreadsheet_field_matching")[2];

    await selectFieldMatching("date", pivotFieldMatching);
    await selectFieldMatching("date", listFieldMatching);
    await selectFieldMatching("date", graphFieldMatching);

    await contains(graphFieldMatching.querySelector("select")).select("-2");

    await saveGlobalFilter();

    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("My Label");
    expect(globalFilter.defaultValue).toBe("last_month");
    expect(globalFilter.rangeType).toBe("relative");
    expect(globalFilter.type).toBe("date");
    const pivotDomain = model.getters.getPivotComputedDomain(pivotId);
    assertDateDomainEqual("date", "2022-06-15", "2022-07-14", pivotDomain);
    const listDomain = model.getters.getListComputedDomain("1");
    assertDateDomainEqual("date", "2022-06-15", "2022-07-14", listDomain);
    const chartId = model.getters.getOdooChartIds()[0];
    const chartDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
    assertDateDomainEqual("date", "2022-04-16", "2022-05-15", chartDomain);
});

test("Edit the value of a relative date filter", async function () {
    mockDate("2022-07-14 00:00:00");
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "date",
            label: "label",
            defaultValue: "last_week",
            rangeType: "relative",
        },
        {
            pivot: { [pivotId]: { chain: "date", type: "date" } },
        }
    );
    await animationFrame();
    await openGlobalFilterSidePanel();
    await animationFrame();
    const select = target.querySelector(".o-sidePanel select");
    expect([...select.querySelectorAll("option")].map((val) => val.value)).toEqual([
        "",
        ...RELATIVE_DATE_RANGE_TYPES.map((item) => item.type),
    ]);
    await contains(select).select("last_year");
    await animationFrame();

    expect(model.getters.getGlobalFilterValue("42")).toBe("last_year");
    const pivotDomain = model.getters.getPivotComputedDomain(pivotId);
    assertDateDomainEqual("date", "2021-07-15", "2022-07-14", pivotDomain);
});

test("Edit the value to empty of a relative date filter", async () => {
    mockDate("2022-07-14 00:00:00");
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "date",
            label: "label",
            defaultValue: "last_week",
            rangeType: "relative",
        },
        {
            pivot: { [pivotId]: { chain: "date", type: "date" } },
        }
    );
    await animationFrame();
    await openGlobalFilterSidePanel();
    await animationFrame();
    const select = target.querySelector(".o-sidePanel select");
    expect([...select.querySelectorAll("option")].map((val) => val.value)).toEqual([
        "",
        ...RELATIVE_DATE_RANGE_TYPES.map((item) => item.type),
    ]);
    await contains(select).select("");
    await animationFrame();

    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
    const pivotDomain = model.getters.getPivotComputedDomain(pivotId);

    expect(pivotDomain).toEqual([]);
});

test("Create a new from_to date filter", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    insertChartInSpreadsheet(model);
    await animationFrame();
    await openGlobalFilterSidePanel();
    await clickCreateFilter("date");
    await editGlobalFilterLabel("My Label");

    const range = target.querySelector(".o-filter-range-type");
    await contains(range).select("from_to");
    await saveGlobalFilter();
    const [globalFilter] = model.getters.getGlobalFilters();
    expect(globalFilter.label).toBe("My Label");
    expect(globalFilter.rangeType).toBe("from_to");
    expect(globalFilter.type).toBe("date");
    expect(globalFilter.defaultValue).toBe(undefined);
});

test("Choose any year in a year picker by clicking the picker", async function () {
    mockDate("2022-07-10 00:00:00");
    const { model } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);

    await openGlobalFilterSidePanel();

    const pivots = target.querySelectorAll(".pivot_filter_section");
    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(pivots[0].querySelector(".o_side_panel_filter_label")).toHaveText(
        THIS_YEAR_GLOBAL_FILTER.label
    );

    expect(".pivot_filter_input input.o_datetime_input").toHaveCount(1);
    const year = pivots[0].querySelector(".pivot_filter_input input.o_datetime_input");

    const this_year = luxon.DateTime.utc().year;
    expect(year).toHaveValue(String(this_year));

    await contains(year).click();

    expect(target.querySelector(".o_datetime_picker")).not.toBe(null, {
        message: "The picker is visible", // Note: don't check actual visibility, because it spawns with an animation and opacity: 0
    });
    expect("button.o_zoom_out.o_datetime_button").toHaveProperty("title", "Select decade", {
        message: "The picker should be displaying the years",
    });

    await contains("button.o_date_item_cell:contains(2024)").click();

    expect(year).toHaveValue("2024");
    expect(model.getters.getGlobalFilterValue(THIS_YEAR_GLOBAL_FILTER.id)).toEqual({
        period: undefined,
        yearOffset: 2,
    });
});

test("Choose any year in a year picker via input", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);

    await openGlobalFilterSidePanel();

    const pivots = target.querySelectorAll(".pivot_filter_section");
    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(pivots[0].querySelector(".o_side_panel_filter_label")).toHaveText(
        THIS_YEAR_GLOBAL_FILTER.label
    );

    expect(".pivot_filter_input input.o_datetime_input").toHaveCount(1);
    const year = pivots[0].querySelector(".pivot_filter_input input.o_datetime_input");

    const this_year = luxon.DateTime.utc().year;
    expect(year).toHaveValue(String(this_year));

    await selectYear(String(this_year - 127));
    expect(year).toHaveValue(String(this_year - 127));
    expect(model.getters.getGlobalFilterValue(THIS_YEAR_GLOBAL_FILTER.id)).toEqual({
        period: undefined,
        yearOffset: -127,
    });

    await selectYear(String(this_year + 32));
    expect(year).toHaveValue(String(this_year + 32));
    expect(model.getters.getGlobalFilterValue(THIS_YEAR_GLOBAL_FILTER.id)).toEqual({
        period: undefined,
        yearOffset: 32,
    });
});

test("Readonly user can update text filter values", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: "abc",
    });
    model.updateMode("readonly");
    await animationFrame();

    await openGlobalFilterSidePanel();

    const pivots = target.querySelectorAll(".pivot_filter_section");
    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(0);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(pivots[0].querySelector(".o_side_panel_filter_label")).toHaveText("Text Filter");

    const input = pivots[0].querySelector(".pivot_filter_input input");
    expect(input).toHaveValue("abc");

    await contains(input).edit("something");

    expect(model.getters.getGlobalFilterValue("42")).toBe("something");
});

test("Readonly user can update date filter values", async function () {
    mockDate("2022-11-10 00:00:00");
    const { model } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(model, {
        id: "43",
        type: "date",
        label: "Date Filter",
        rangeType: "fixedPeriod",
        defaultValue: "this_quarter",
    });
    model.updateMode("readonly");
    await animationFrame();

    await openGlobalFilterSidePanel();

    const pivots = target.querySelectorAll(".pivot_filter_section");
    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(0);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(pivots[0].querySelector(".o_side_panel_filter_label")).toHaveText("Date Filter");

    expect(".pivot_filter_input div.date_filter_values select").toHaveCount(1);
    const quarter = pivots[0].querySelector(".pivot_filter_input div.date_filter_values select");
    expect(".pivot_filter_input input.o_datetime_input").toHaveCount(1);
    const year = pivots[0].querySelector(".pivot_filter_input input.o_datetime_input");
    expect(quarter).toHaveValue("fourth_quarter");
    expect(year).toHaveValue("2022");
    await contains(quarter).select("second_quarter");
    await animationFrame();
    await selectYear("2021");
    await animationFrame();

    expect(quarter).toHaveValue("second_quarter");
    expect(year).toHaveValue("2021");

    expect(model.getters.getGlobalFilterValue("43")).toEqual({
        period: "second_quarter",
        yearOffset: -1,
    });
});

test("Readonly user can update relation filter values", async function () {
    const tagSelector = ".o_multi_record_selector .badge";
    const { model } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "Relation Filter",
        modelName: "product",
        defaultValue: [41],
    });
    expect(model.getters.getGlobalFilters().length).toBe(1);
    model.updateMode("readonly");
    await animationFrame();

    await openGlobalFilterSidePanel();

    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(0);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(".pivot_filter_section .o_side_panel_filter_label").toHaveText("Relation Filter");
    expect(tagSelector).toHaveCount(1);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual(["xpad"]);

    await contains(".pivot_filter_section .pivot_filter_input input.o-autocomplete--input").click();
    await contains("ul.ui-autocomplete li:first-child").click();

    expect(tagSelector).toHaveCount(2);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual(["xpad", "xphone"]);
    expect(model.getters.getGlobalFilterValue("42")).toEqual([41, 37]);
});

test("Change all domains -> Set corresponding model should allow saving", async function () {
    const serverData = getBasicServerData();
    defineModels([Vehicle]);
    const vehicle_ids = fields.Many2many({ relation: "vehicle", string: "Vehicle" });
    Partner._fields.vehicle_ids = vehicle_ids;
    serverData.models["ir.model"].records = [
        ...IrModel._records,
        {
            id: 34,
            name: "Vehicle",
            model: "vehicle",
        },
    ];

    const { model } = await createSpreadsheetFromPivotView({ serverData });
    const label = "Product";
    await openGlobalFilterSidePanel();
    await clickCreateFilter("relation");
    await selectModelForRelation("product");
    await saveGlobalFilter();
    await contains(".o-sidePanel .fa-cog").click();

    expect(".o_global_filter_label").toHaveValue(label);

    // visible: false to skip the collapsible. We really don't want to use the collapsible here, as bootstrap dispatches
    // scroll events which have the side effect to close the autocomplete
    await contains(".o_model_field_selector_value", { visible: false }).click();
    await contains(target.querySelectorAll(".o_model_field_selector_popover_item")[3]).click();
    await contains(".o_model_field_selector_popover_close").click();
    await selectModelForRelation("vehicle");

    await editGlobalFilterLabel("test case");
    await saveGlobalFilter();
    expect(model.getters.getGlobalFilters()[0].label).toBe("test case");
});

test("Can clear a text filter values", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "text",
            label: "Text Filter",
            defaultValue: "",
        },
        {
            pivot: { [pivotId]: { chain: "name", type: "char" } },
        }
    );
    await openGlobalFilterSidePanel();

    const pivots = target.querySelectorAll(".pivot_filter_section");
    const input = pivots[0].querySelector(".pivot_filter_input input");
    expect(input).toHaveValue("");
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(1);
    // no default value
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);

    await contains(input).edit("something");
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([["name", "ilike", "something"]]);

    await contains("i.o_side_panel_filter_icon.fa-times").click();
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);
    expect(input).toHaveValue("");
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Can clear a date filter values", async function () {
    mockDate("2022-11-10 00:00:00");
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "43",
            type: "date",
            label: "Date Filter",
            rangeType: "fixedPeriod",
            defaultValue: { yearOffset: undefined, period: undefined },
        },
        {
            pivot: { [pivotId]: { chain: "date", type: "date" } },
        }
    );
    await openGlobalFilterSidePanel();
    const pivots = target.querySelectorAll(".pivot_filter_section");
    const quarter = pivots[0].querySelector(".pivot_filter_input div.date_filter_values select");
    const year = pivots[0].querySelector(".pivot_filter_input input.o_datetime_input");
    expect(quarter).toHaveValue("empty");
    expect(year.placeholder).toBe("Select year...");
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(1);
    // no default value
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);

    await contains(quarter).select("second_quarter");
    await selectYear("2021");
    expect(quarter).toHaveValue("second_quarter");
    expect(year).toHaveValue("2021");
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([
        "&",
        ["date", ">=", "2021-04-01"],
        ["date", "<=", "2021-06-30"],
    ]);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);

    await contains("i.o_side_panel_filter_icon.fa-times").click();
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);
    expect(quarter).toHaveValue("empty");
    expect(year.placeholder).toBe("Select year...");
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Can clear a relation filter values", async function () {
    const tagSelector = ".o_multi_record_selector .badge";
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "Relation Filter",
            modelName: "product",
            defaultValue: [],
        },
        {
            pivot: { [pivotId]: { chain: "product_id", type: "many2one" } },
        }
    );
    expect(model.getters.getGlobalFilters().length).toBe(1);

    await openGlobalFilterSidePanel();

    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);
    expect(".pivot_filter_section .o_side_panel_filter_label").toHaveText("Relation Filter");
    expect(tagSelector).toHaveCount(0);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual([]);

    await contains(".pivot_filter_section .pivot_filter_input input.o-autocomplete--input").click();
    await contains("ul.ui-autocomplete li:first-child").click();

    expect(tagSelector).toHaveCount(1);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual(["xphone"]);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([["product_id", "in", [37]]]);

    // clear filter
    await contains("i.o_side_panel_filter_icon.fa-times").click();
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);
    expect(tagSelector).toHaveCount(0);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual([]);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Can clear automatic default user with the global clear button", async function () {
    const uid = user.userId;
    const tagSelector = ".o_multi_record_selector .badge";
    const serverData = getBasicServerData();
    const { model, pivotId } = await createSpreadsheetFromPivotView({ serverData });
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "Relation Filter",
            modelName: "res.users",
            defaultValue: "current_user",
        },
        {
            pivot: { [pivotId]: { chain: "user_ids", type: "many2many" } },
        }
    );

    await openGlobalFilterSidePanel();
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([["user_ids", "in", [uid]]]);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual(["Mitchell Admin"]);
    // clear filter
    await contains("i.o_side_panel_filter_icon.fa-times").click();
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual([]);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Can clear automatic default user from the record selector tag", async function () {
    const uid = user.userId;
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "Relation Filter",
            modelName: "res.users",
            defaultValue: "current_user",
        },
        {
            pivot: { [pivotId]: { chain: "user_ids", type: "many2many" } },
        }
    );

    await openGlobalFilterSidePanel();
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([["user_ids", "in", [uid]]]);
    // clear filter
    const tagClearButton = target.querySelector(".o_multi_record_selector .o_delete");
    await contains(tagClearButton).click();
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Changing the range of a date global filter reset the default value", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "date",
            rangeType: "fixedPeriod",
            label: "This month",
            defaultValue: "this_month",
        },
        {
            pivot: {
                [pivotId]: { chain: "date", type: "date" },
            },
        }
    );
    await openGlobalFilterSidePanel();
    await contains(".o_side_panel_filter_icon.fa-cog").click();
    const timeRangeOption = target.querySelectorAll(
        ".o_spreadsheet_filter_editor_side_panel .o-section"
    )[1];
    const selectField = timeRangeOption.querySelector("select");
    await contains(selectField).select("fixedPeriod");
    await saveGlobalFilter();
    expect(model.getters.getGlobalFilters()[0].defaultValue).toEqual(undefined);
});

test("Changing the range of a date global filter reset the current value", async function () {
    mockDate("2022-07-10 00:00:00");
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "date",
            label: "label",
            defaultValue: "last_week",
            rangeType: "relative",
        },
        {
            pivot: { [pivotId]: { chain: "date", type: "date" } },
        }
    );
    await animationFrame();
    await openGlobalFilterSidePanel();
    await animationFrame();
    const select = target.querySelector(".o-sidePanel select");
    expect([...select.querySelectorAll("option")].map((val) => val.value)).toEqual([
        "",
        ...RELATIVE_DATE_RANGE_TYPES.map((item) => item.type),
    ]);
    const pivotDomain = model.getters.getPivotComputedDomain(pivotId);
    assertDateDomainEqual("date", "2022-07-04", "2022-07-10", pivotDomain);
    const editFilter = target.querySelector(".o_side_panel_filter_icon.fa-cog");
    expect(model.getters.getGlobalFilterValue("42")).toBe("last_week");

    // Edit filter range and save
    await contains(editFilter).click();
    const timeRangeOption = target.querySelectorAll(
        ".o_spreadsheet_filter_editor_side_panel .o-section"
    )[1];
    const selectField = timeRangeOption.querySelector("select");
    await contains(selectField).select("fixedPeriod");
    await contains("input[name=date_automatic_filter]").click();
    const automaticTimeRangeOption = target.querySelectorAll(
        ".o_spreadsheet_filter_editor_side_panel .o-section"
    )[2];
    const selectPeriodField = automaticTimeRangeOption.querySelector("select");
    await contains(selectPeriodField).select("this_quarter");
    await saveGlobalFilter();

    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        period: "third_quarter",
        yearOffset: 0,
    });
});

test("Date filter automatic filter value checkbox is working", async function () {
    mockDate("2022-07-10 00:00:00");
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "date",
            rangeType: "fixedPeriod",
            label: "date",
        },
        {
            pivot: {
                [pivotId]: { chain: "date", type: "date" },
            },
        }
    );
    await openGlobalFilterSidePanel();
    await contains(".o_side_panel_filter_icon.fa-cog").click();
    await contains("input[name=date_automatic_filter]").click();

    await saveGlobalFilter();
    await animationFrame();
    expect(model.getters.getGlobalFilter("42").defaultValue).toBe("this_month");
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        yearOffset: 0,
        period: "july",
    });
    await contains(".o_side_panel_filter_icon.fa-cog").click();
    await contains("input[name=date_automatic_filter]").click();
    await saveGlobalFilter();
    await animationFrame();
    expect(model.getters.getGlobalFilter("42").defaultValue).toBe(undefined);
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
});

test("Filter edit side panel is initialized with the correct values", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "date",
            rangeType: "fixedPeriod",
            label: "This month",
            defaultValue: "this_month",
        },
        {
            pivot: {
                [pivotId]: { chain: "date", type: "date", offset: 0 },
            },
            list: {
                1: { chain: "date", type: "date", offset: 1 },
            },
        }
    );
    await openGlobalFilterSidePanel();
    await contains(".o-sidePanel .fa-cog").click();

    expect(".o-sidePanel .o-input:eq(0)").toHaveValue("This month");
    expect(".o-sidePanel .o-input:eq(1)").toHaveValue("fixedPeriod");

    const pivotField = ".o-sidePanel .o_spreadsheet_field_matching:eq(0)";
    const pivotFieldValue = `${pivotField} .o_model_field_selector_value span`;
    expect(pivotFieldValue).toHaveText("Date");
    expect(`${pivotField} select`).toHaveValue("0");

    const listField = ".o-sidePanel .o_spreadsheet_field_matching:eq(1)";
    const listFieldValue = `${listField} .o_model_field_selector_value span`;
    expect(listFieldValue).toHaveText("Date");
    expect(`${listField} select`).toHaveValue("1");
});

test("Empty field is marked as warning", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: "",
    });
    await openGlobalFilterSidePanel();
    await contains("i.o_side_panel_filter_icon.fa-cog").click();
    expect(target.querySelector(".o_spreadsheet_field_matching")).toHaveClass("o_missing_field");
});

test("Can save with an empty field", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: "",
    });
    await openGlobalFilterSidePanel();
    await contains("i.o_side_panel_filter_icon.fa-cog").click();
    await saveGlobalFilter();
    expect(model.getters.getPivotFieldMatching(pivotId, "42")).toEqual({});
});

test("Can reorder filters with drag & drop", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    addGlobalFilter(model, LAST_YEAR_GLOBAL_FILTER);
    let filters = model.getters.getGlobalFilters();
    expect(filters[0].id).toBe(THIS_YEAR_GLOBAL_FILTER.id);
    expect(filters[1].id).toBe(LAST_YEAR_GLOBAL_FILTER.id);
    await openGlobalFilterSidePanel();
    const handle = target.querySelector(".o-filter-drag-handle");
    const sections = target.querySelectorAll(".pivot_filter_section");

    await contains(handle, { visible: false }).dragAndDrop(sections[1], { position: "bottom" });

    filters = model.getters.getGlobalFilters();
    expect(filters[0].id).toBe(LAST_YEAR_GLOBAL_FILTER.id);
    expect(filters[1].id).toBe(THIS_YEAR_GLOBAL_FILTER.id);
});

test("Can clear a field matching an invalid field", async function () {
    const { model, pivotId } = await createSpreadsheetFromPivotView();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "text",
            label: "Text Filter",
            defaultValue: "",
            name: "test",
        },
        {
            pivot: {
                [pivotId]: { chain: "not_a_field", type: "" },
            },
        }
    );
    await openGlobalFilterSidePanel();
    await contains("i.o_side_panel_filter_icon.fa-cog").click();
    await contains(".o-sidePanel .collapsor").click(); // uncollapse the field matching
    expect(".o_model_field_selector_warning").toHaveCount(1);
    expect(".o_spreadsheet_field_matching .o_model_field_selector").toHaveText("not_a_field");
    await contains(".o_model_field_selector .fa.fa-times").click();
    expect(".o_spreadsheet_field_matching .o_model_field_selector").toHaveText("");
});

test("Can change fixedPeriod date filter disabledPeriods in the side panel", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    const filter = /** @type {FixedPeriodDateGlobalFilter} */ ({
        id: "43",
        type: "date",
        label: "Date Filter",
        rangeType: "fixedPeriod",
    });
    await addGlobalFilter(model, filter);
    await openGlobalFilterSidePanel();
    await contains("i.o_side_panel_filter_icon.fa-cog").click();

    expect(target.querySelector("input[name='month']").checked).toBe(true);
    await contains('input[name="month"]').click();
    await saveGlobalFilter();

    expect(model.getters.getGlobalFilter("43").disabledPeriods).toEqual(["month"]);

    await contains("i.o_side_panel_filter_icon.fa-cog").click();
    expect(target.querySelector("input[name='month']").checked).toBe(false);
});

test("fixedPeriod date filter possible values change with disabledPeriods ", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    const filter = /** @type {FixedPeriodDateGlobalFilter} */ ({
        id: "43",
        type: "date",
        label: "Date Filter",
        rangeType: "fixedPeriod",
    });
    await addGlobalFilter(model, filter);
    await openGlobalFilterSidePanel();

    const filterValuesSelect = target.querySelector(".date_filter_values select");
    let options = [...filterValuesSelect.querySelectorAll("option")].map((option) => option.value);

    expect(options).toEqual(["empty", ...quarterOptionsIds, ...monthsOptionsIds]);

    await editGlobalFilter(model, { ...filter, disabledPeriods: ["month"] });
    await animationFrame();
    options = [...filterValuesSelect.querySelectorAll("option")].map((option) => option.value);
    expect(options).toEqual(["empty", ...quarterOptionsIds]);

    await editGlobalFilter(model, { ...filter, disabledPeriods: ["quarter"] });
    options = [...filterValuesSelect.querySelectorAll("option")].map((option) => option.value);
    expect(options).toEqual(["empty", ...monthsOptionsIds]);

    await editGlobalFilter(model, { ...filter, disabledPeriods: ["month", "quarter"] });
    expect(".date_filter_values select").toHaveCount(0);
});

test("invalid fixed period automatic value is removed when changing disabledPeriods", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    const filter = /** @type {FixedPeriodDateGlobalFilter} */ ({
        id: "43",
        type: "date",
        label: "Date Filter",
        rangeType: "fixedPeriod",
        defaultValue: "this_month",
    });
    await addGlobalFilter(model, filter);
    await openGlobalFilterSidePanel();
    await contains("i.o_side_panel_filter_icon.fa-cog").click();

    expect(".date_filter_automatic_value").toHaveValue("this_month");

    // Disable "month" period
    await contains(".o-sidePanelBody input[name='month']").click();
    expect(".date_filter_automatic_value").toHaveValue("this_year");
    expect(queryAllValues(".date_filter_automatic_value option")).toEqual([
        "this_year",
        "this_quarter",
    ]);
});

test("Disabled period section is not present for non fixedPeriod date filters", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    const filter = /** @type {FixedPeriodDateGlobalFilter} */ ({
        id: "43",
        type: "date",
        label: "Date Filter",
        rangeType: "fixedPeriod",
    });
    await addGlobalFilter(model, filter);
    await openGlobalFilterSidePanel();
    await contains("i.o_side_panel_filter_icon.fa-cog").click();

    expect("input[name='month']").toHaveCount(1);

    const range = target.querySelector(".o-filter-range-type");
    await contains(range).select("from_to");
    expect("input[name='month']").toHaveCount(0);

    await contains(range).select("relative");
    expect("input[name='month']").toHaveCount(0);
});

test("Cannot create a filter if a datasource is in error", async function () {
    const spreadsheetData = {
        lists: {
            1: {
                id: 1,
                columns: ["foo", "contact_name"],
                domain: [],
                model: "unknown",
                orderBy: [],
                context: {},
                fieldMatching: {},
            },
        },
    };
    const serverData = getBasicServerData();
    serverData.models["documents.document"].records = [
        DocumentsDocument._records[0], // res_company.document_spreadsheet_folder_id
        {
            id: 45,
            spreadsheet_data: JSON.stringify(spreadsheetData),
            name: "Spreadsheet",
            handler: "spreadsheet",
        },
    ];
    await createSpreadsheet({
        serverData,
        spreadsheetId: 45,
        mockRPC: async function (route, { model, method, kwargs }) {
            if (model === "unknown" && method === "fields_get") {
                throw makeServerError({ code: 404 });
            }
        },
    });
    await openGlobalFilterSidePanel();
    for (const type of Object.keys(FILTER_CREATION_SELECTORS)) {
        await clickCreateFilter(type);
        expect(".o-validation-error").toHaveCount(1);
        expect(".o_global_filter_save").toHaveCount(0);
        await cancelGlobalFilterEdition();
    }
});

test("Default value and subdomain are hidden for invalid relational filters", async () => {
    const { model } = await createSpreadsheetFromPivotView({
        mockRPC: async function (route, { model, method, kwargs }) {
            if (model === "unknown" && method === "fields_get") {
                throw makeServerError({ code: 404 });
            }
        },
    });
    const filter = /** @type {FixedPeriodDateGlobalFilter} */ ({
        id: "43",
        type: "relation",
        label: "Relational Filter",
        modelName: "unknown",
    });
    await addGlobalFilter(model, filter);
    await openGlobalFilterSidePanel();
    expect(".o-filter-value .o-validation").toHaveCount(1);
    await contains(".o_side_panel_filter_icon.fa-cog").click();
    expect(".o_multi_record_selector").toHaveCount(0);
});
