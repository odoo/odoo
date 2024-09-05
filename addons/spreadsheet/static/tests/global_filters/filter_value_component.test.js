import { makeMockEnv, contains, onRpc } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { describe, expect, test, getFixture, mountOnFixture } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { click } from "@odoo/hoot-dom";

import { Model } from "@odoo/o-spreadsheet";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import {
    addGlobalFilter,
    setCellContent,
    setCellFormat,
} from "@spreadsheet/../tests/helpers/commands";
import { toRangeData } from "@spreadsheet/../tests/helpers/zones";
import { getTemplate } from "@web/core/templates";
import { user } from "@web/core/user";

import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";

describe.current.tags("headless");
defineSpreadsheetModels();

/**
 *
 * @param {{ model: Model, filter: object}} props
 */
async function mountFilterValueComponent(env, props) {
    await mountOnFixture(FilterValue, { props, env, getTemplate });
}

test("basic text filter", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFilterValueComponent(env, { model, filter: model.getters.getGlobalFilter("42") });
    await contains("input").edit("foo");
    expect(model.getters.getGlobalFilterValue("42")).toBe("foo", { message: "value is set" });
});

test("text filter with range", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const sheetId = model.getters.getActiveSheetId();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangeOfAllowedValues: toRangeData(sheetId, "A1:A3"),
    });
    setCellContent(model, "A1", "foo");
    setCellContent(model, "A2", "0");
    setCellFormat(model, "A2", "0.00");
    await mountFilterValueComponent(env, { model, filter: model.getters.getGlobalFilter("42") });
    const fixture = getFixture();
    const select = fixture.querySelector("select");
    const options = [...fixture.querySelectorAll("option")];
    const optionsLabels = options.map((el) => el.textContent);
    const optionsValues = options.map((el) => el.value);
    expect(select.value).toBe("", { message: "no value is selected" });
    expect(optionsLabels).toEqual(["Choose a value...", "foo", "0.00"], {
        message: "values are formatted",
    });
    expect(optionsValues).toEqual(["", "foo", "0"]);
    await contains("select").select("0");
    expect(select.value).toBe("0", { message: "value is selected" });
    expect(model.getters.getGlobalFilterValue("42")).toBe("0", { message: "value is set" });
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
        type: "relation",
        label: "My Filter",
        modelName: "partner",
        domainOfAllowedValues: [["display_name", "=", "Bob"]],
    });
    await mountFilterValueComponent(env, { model, filter: model.getters.getGlobalFilter("42") });
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
        type: "relation",
        label: "My Filter",
        modelName: "partner",
        domainOfAllowedValues: '[["user_ids", "in", [uid]]]',
    });
    await mountFilterValueComponent(env, { model, filter: model.getters.getGlobalFilter("42") });
    await click(".o_multi_record_selector input");
    await animationFrame();
    expect.verifySteps(["name_search"]);
});
