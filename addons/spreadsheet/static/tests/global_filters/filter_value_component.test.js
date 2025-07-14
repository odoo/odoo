import { describe, expect, test } from "@odoo/hoot";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { contains, makeMockEnv, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { Model } from "@odoo/o-spreadsheet";
import {
    addGlobalFilter,
    editGlobalFilter,
    setCellContent,
    setCellFormat,
} from "@spreadsheet/../tests/helpers/commands";
import { toRangeData } from "@spreadsheet/../tests/helpers/zones";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import { user } from "@web/core/user";

import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { Component, onWillUnmount, xml } from "@odoo/owl";

describe.current.tags("headless");
defineSpreadsheetModels();

class FilterValueWrapper extends Component {
    static template = xml`
        <FilterValue
            t-props="props"
            globalFilterValue="globalFilterValue"
        />`;
    static components = { FilterValue };
    static props = FilterValue.props;

    setup() {
        this.props.model.on("update", this, () => this.render(true));
        onWillUnmount(() => this.props.model.off("update", this));
    }

    get globalFilterValue() {
        return (
            this.props.globalFilterValue ??
            this.props.model.getters.getGlobalFilterValue(this.props.filter.id)
        );
    }
}

/**
 *
 * @param {{ model: Model, filter: object}} props
 */
async function mountFilterValueComponent(props) {
    props = {
        setGlobalFilterValue: (id, value, displayNames) => {
            props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
                id,
                value,
                displayNames,
            });
        },
        ...props,
    };
    await mountWithCleanup(FilterValueWrapper, { props });
}

test("basic text filter", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    await contains(".o-autocomplete input").edit("foo");
    await contains(".o-autocomplete input").press("Enter");
    expect(model.getters.getGlobalFilterValue("42")).toEqual(
        { operator: "ilike", strings: ["foo"] },
        { message: "value is set" }
    );
});

test("can clear a text filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: { operator: "ilike", strings: ["foo", "bar"] },
    });
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    expect(queryAllTexts(".o_tag")).toEqual(["foo", "bar"]);
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        operator: "ilike",
        strings: ["foo", "bar"],
    });
    await contains(".o_tag .o_delete", { visible: false }).click();
    expect(queryAllTexts(".o_tag")).toEqual(["bar"]);
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        operator: "ilike",
        strings: ["bar"],
    });
});

test("text filter with range", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const sheetId = model.getters.getActiveSheetId();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A3")],
    });
    setCellContent(model, "A1", "foo");
    setCellContent(model, "A2", "0");
    setCellFormat(model, "A2", "0.00");
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    expect(".o_tag").toHaveCount(0, { message: "no value is selected" });
    await click(".o-autocomplete input");
    await animationFrame();

    expect(queryAllTexts(".dropdown-item")).toEqual(["foo", "0.00"], {
        message: "values are formatted",
    });
    await click(".dropdown-item:last");
    await animationFrame();
    expect(".o_tag").toHaveText("0.00");
    expect(model.getters.getGlobalFilterValue("42").strings).toEqual(["0"]);

    // select a second value
    await click(".o-autocomplete input");
    await animationFrame();

    await click(".dropdown-item:last");
    await animationFrame();
    expect(queryAllTexts(".o_tag")).toEqual(["0.00", "foo"]);
    expect(model.getters.getGlobalFilterValue("42").strings).toEqual(["0", "foo"]);
});

test("cannot edit text filter input with range", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "foo");
    const filter = {
        id: "42",
        type: "text",
        label: "Text Filter",
    };
    await addGlobalFilter(model, filter);
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    expect(".o-autocomplete input").not.toHaveAttribute("maxlength");
    editGlobalFilter(model, {
        ...filter,
        rangesOfAllowedValues: [toRangeData(sheetId, "A1")],
    });
    await animationFrame();
    expect(".o-autocomplete input").toHaveAttribute("maxlength", "0");
    editGlobalFilter(model, filter);
    await animationFrame();
    expect(".o-autocomplete input").not.toHaveAttribute("maxlength");
});

test("text filter cannot have the same value twice", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    await contains(".o-autocomplete input").edit("foo");
    await contains(".o-autocomplete input").press("Enter");
    await contains(".o-autocomplete input").edit("foo");
    await contains(".o-autocomplete input").press("Enter");
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        operator: "ilike",
        strings: ["foo"],
    });
});

test("relational filter with domain", async function () {
    onRpc("partner", "name_search", ({ kwargs }) => {
        expect.step("name_search");
        expect(kwargs.domain).toEqual(["&", ["display_name", "=", "Bob"], "!", ["id", "in", []]]);
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
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    await click(".o_multi_record_selector input");
    await animationFrame();
    expect.verifySteps(["name_search"]);
});

test("Filter with showClear should display the clear icon", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: { operator: "ilike", strings: ["foo"] },
    });
    await mountFilterValueComponent({
        model,
        filter: model.getters.getGlobalFilter("42"),
        showClear: true,
    });
    expect(".fa-times").toHaveCount(1);
});

test("Filter without showClear should not display the clear icon", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: { operator: "ilike", strings: ["foo"] },
    });
    await mountFilterValueComponent({
        model,
        filter: model.getters.getGlobalFilter("42"),
    });
    expect(".fa-times").toHaveCount(0);
});

test("relational filter with a contextual domain", async function () {
    onRpc("partner", "name_search", ({ kwargs }) => {
        expect.step("name_search");
        expect(kwargs.domain).toEqual([
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
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    await click(".o_multi_record_selector input");
    await animationFrame();
    expect.verifySteps(["name_search"]);
});

test("selection filter", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "selection",
        label: "Selection Filter",
        resModel: "res.currency",
        selectionField: "position",
    });
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    await contains("input").click();
    await contains("a:first").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        operator: "in",
        selectionValues: ["after"],
    });
});

test("numeric filter", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "numeric",
        label: "Numeric Filter",
        defaultValue: { operator: "=", targetValue: 1998 },
    });
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    await contains("input").edit(1998);
    await contains("input").press("Enter");
    expect(model.getters.getGlobalFilterValue("42")).toEqual(
        { operator: "=", targetValue: 1998 },
        { message: "value is set" }
    );
});
