import { describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { ModelSelector } from "@web/core/model_selector/model_selector";

async function mountModelSelector(models = [], value = undefined, onModelSelected = () => {}) {
    await mountWithCleanup(ModelSelector, {
        props: {
            models,
            value,
            onModelSelected,
        },
    });
}

class IrModel extends models.Model {
    _name = "ir.model";

    name = fields.Char({ string: "Model Name" });
    model = fields.Char();
    _records = [
        { id: 1, name: "Model 1", model: "model_1" },
        { id: 2, name: "Model 2", model: "model_2" },
        { id: 3, name: "Model 3", model: "model_3" },
        { id: 4, name: "Model 4", model: "model_4" },
        { id: 5, name: "Model 5", model: "model_5" },
        { id: 6, name: "Model 6", model: "model_6" },
        { id: 7, name: "Model 7", model: "model_7" },
        { id: 8, name: "Model 8", model: "model_8" },
        { id: 9, name: "Model 9", model: "model_9" },
        { id: 10, name: "Model 10", model: "model_10" },
    ];
}

defineModels([IrModel]);
describe.current.tags("desktop");

onRpc("ir.model", "display_name_for", function ({ args }) {
    const models = args[0];
    const records = this.env["ir.model"].filter((rec) => models.includes(rec.model));
    return records.map((record) => ({
        model: record.model,
        display_name: record.name,
    }));
});

test("model_selector: with no model", async () => {
    await mountModelSelector();
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(1);
    expect("li.o-autocomplete--dropdown-item").toHaveText("No records");
});

test("model_selector: displays model display names", async () => {
    await mountModelSelector(["model_1", "model_2", "model_3"]);
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(3);
    const items = queryAll("li.o-autocomplete--dropdown-item");
    expect(items[0]).toHaveText("Model 1");
    expect(items[1]).toHaveText("Model 2");
    expect(items[2]).toHaveText("Model 3");
});

test("model_selector: with 8 models", async () => {
    await mountModelSelector([
        "model_1",
        "model_2",
        "model_3",
        "model_4",
        "model_5",
        "model_6",
        "model_7",
        "model_8",
    ]);
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(8);
});

test("model_selector: with more than 8 models", async () => {
    await mountModelSelector([
        "model_1",
        "model_2",
        "model_3",
        "model_4",
        "model_5",
        "model_6",
        "model_7",
        "model_8",
        "model_9",
        "model_10",
    ]);
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(9);
    expect("li.o-autocomplete--dropdown-item:eq(8)").toHaveText("Start typing...");
});

test("model_selector: search content is not applied when opening the autocomplete", async () => {
    await mountModelSelector(["model_1", "model_2"], "_2");
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(2);
});

test("model_selector: with search matching some records on technical name", async () => {
    await mountModelSelector(["model_1", "model_2"]);
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--input").edit("_2", { confirm: false });
    await runAllTimers();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(1);
    expect("li.o-autocomplete--dropdown-item").toHaveText("Model 2");
});

test("model_selector: with search matching some records on business name", async () => {
    await mountModelSelector(["model_1", "model_2"]);
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--input").edit(" 2", { confirm: false });
    await runAllTimers();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(1);
    expect("li.o-autocomplete--dropdown-item").toHaveText("Model 2");
});

test("model_selector: with search matching no record", async () => {
    await mountModelSelector(["model_1", "model_2"]);
    await contains(".o-autocomplete--input").edit("a random search query", { confirm: false });
    await runAllTimers();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(1);
    expect("li.o-autocomplete--dropdown-item").toHaveText("No records");
});

test("model_selector: select a model", async () => {
    await mountModelSelector(["model_1", "model_2", "model_3"], "Model 1", (selected) => {
        expect.step("model selected");
        expect(selected).toEqual({
            label: "Model 2",
            technical: "model_2",
        });
    });
    await contains(".o-autocomplete--input").click();
    await contains(".o_model_selector_model_2").click();
    expect.verifySteps(["model selected"]);
});

test("model_selector: click on start typing", async () => {
    await mountModelSelector([
        "model_1",
        "model_2",
        "model_3",
        "model_4",
        "model_5",
        "model_6",
        "model_7",
        "model_8",
        "model_9",
        "model_10",
    ]);
    await contains(".o-autocomplete--input").click();
    await contains("li.o-autocomplete--dropdown-item:eq(8)").click();
    expect(".o-autocomplete--input").toHaveValue("");
    expect(".o-autocomplete.dropdown ul").toHaveCount(0);

    //label must be empty
    expect(".o_global_filter_label").toHaveCount(0);

    //Default value and matching fields should not be available
    expect(".o_side_panel_section").toHaveCount(0);
});

test("model_selector: with an initial value", async () => {
    await mountModelSelector(["model_1", "model_2", "model_3"], "Model 1");
    expect(".o-autocomplete--input").toHaveValue("Model 1");
});
