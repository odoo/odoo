import { describe, expect, test } from "@odoo/hoot";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { contains, makeMockEnv, onRpc } from "@web/../tests/web_test_helpers";

import { Model } from "@odoo/o-spreadsheet";
import {
    addGlobalFilter,
    setCellContent,
    setCellFormat,
} from "@spreadsheet/../tests/helpers/commands";
import { toRangeData } from "@spreadsheet/../tests/helpers/zones";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import { user } from "@web/core/user";

import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { mountComponentWithModelUpdate } from "../helpers/ui";

describe.current.tags("desktop");
defineSpreadsheetModels();

/**
 *
 * @param {{ model: Model, filter: object}} props
 */
async function mountFilterValueComponent(props) {
    await mountComponentWithModelUpdate(FilterValue, props);
}

test("basic text filter", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        operator: "ilike",
        label: "Text Filter",
        target: { model: "lead", field: "char_field" },
    });
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    await contains("input").edit("foo");
    expect(model.getters.getGlobalFilterValue("42")).toBe("foo", { message: "value is set" });
});

test("text filter with range", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const sheetId = model.getters.getActiveSheetId();
    await addGlobalFilter(model, {
        id: "42",
        operator: "ilike",
        label: "Text Filter",
        rangeOfAllowedValues: toRangeData(sheetId, "A1:A3"),
        target: { model: "lead", field: "char_field" },
    });
    setCellContent(model, "A1", "foo");
    setCellContent(model, "A2", "0");
    setCellFormat(model, "A2", "0.00");
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    expect(".o-autocomplete input").toHaveValue("", { message: "no value is selected" });
    await contains("input").click();
    expect(queryAllTexts("li")).toEqual(["foo", "0.00"], {
        message: "values are formatted",
    });
    await contains("li a").click();
    expect(".o-autocomplete input").toHaveValue("foo", { message: "value is selected" });
    expect(model.getters.getGlobalFilterValue("42")).toBe("foo", { message: "value is set" });
});

test("relational filter with domain", async function () {
    onRpc("partner", "name_search", ({ kwargs }) => {
        expect.step("name_search");
        expect(kwargs.args).toEqual(["&", ["display_name", "=", "Bob"], "!", ["id", "in", []]]);
    });
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        operator: "in",
        label: "My Filter",
        relation: "partner",
        domainOfAllowedValues: [["display_name", "=", "Bob"]],
        target: { model: "lead", field: "partner" },
    });
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    await click(".o_multi_record_selector input");
    await animationFrame();
    expect.verifySteps(["name_search"]);
});

test("relational filter with a contextual domain", async function () {
    onRpc("partner", "name_search", ({ kwargs }) => {
        expect.step("name_search");
        expect(kwargs.args).toEqual([
            "&",
            ["user_ids", "in", [user.userId]],
            "!",
            ["id", "in", []],
        ]);
    });
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        operator: "in",
        label: "My Filter",
        relation: "partner",
        domainOfAllowedValues: '[["user_ids", "in", [uid]]]',
        target: { model: "lead", field: "partner" },
    });
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    await click(".o_multi_record_selector input");
    await animationFrame();
    expect.verifySteps(["name_search"]);
});
