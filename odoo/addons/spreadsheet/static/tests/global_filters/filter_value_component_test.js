/** @odoo-module */

import { Model } from "@odoo/o-spreadsheet";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import { addGlobalFilter, setCellContent, setCellFormat } from "../utils/commands";
import { toRangeData } from "../utils/zones";
import { editInput, editSelect, getFixture, mount } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { nameService } from "@web/core/name_service";

function beforeEach() {
    registry.category("services").add("name", nameService);
}

QUnit.module("FilterValue component", { beforeEach });

/**
 *
 * @param {{ model: Model, filter: object}} props
 */
async function mountFilterValueComponent(props) {
    const fixture = getFixture();
    const env = await makeTestEnv();
    await mount(FilterValue, fixture, { props, env });
}

QUnit.test("basic text filter", async function (assert) {
    const model = new Model();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    const fixture = getFixture();
    await editInput(fixture, "input", "foo");
    assert.strictEqual(model.getters.getGlobalFilterValue("42"), "foo", "value is set");
});

QUnit.test("text filter with range", async function (assert) {
    const model = new Model();
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
    await mountFilterValueComponent({ model, filter: model.getters.getGlobalFilter("42") });
    const fixture = getFixture();
    const select = fixture.querySelector("select");
    const options = [...fixture.querySelectorAll("option")];
    const optionsLabels = options.map((el) => el.textContent);
    const optionsValues = options.map((el) => el.value);
    assert.strictEqual(select.value, "", "no value is selected");
    assert.deepEqual(optionsLabels, ["Choose a value...", "foo", "0.00"], "values are formatted");
    assert.deepEqual(optionsValues, ["", "foo", "0"]);
    await editSelect(fixture, "select", "0");
    assert.strictEqual(select.value, "0", "value is selected");
    assert.strictEqual(model.getters.getGlobalFilterValue("42"), "0", "value is set");
});
