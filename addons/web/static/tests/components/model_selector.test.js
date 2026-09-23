// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { queryAll, queryOne } from "@odoo/hoot-dom";
import { animationFrame, Deferred, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { ModelSelector } from "@web/components/model_selector/model_selector";

async function mountModelSelector(
    models = [],
    value = undefined,
    onModelSelected = () => {},
    nbVisibleModels = undefined,
) {
    await mountWithCleanup(ModelSelector, {
        props: {
            models,
            value,
            onModelSelected,
            nbVisibleModels,
        },
    });
}

class IrModel extends models.Model {
    _name = "ir.model";

    name = fields.Char({ string: "Model Name" });
    model = fields.Char();
    _records = [
        { id: 1, name: "Model 1", model: "model.1" },
        { id: 2, name: "Model 2", model: "model.2" },
        { id: 3, name: "Model 3", model: "model.3" },
        { id: 4, name: "Model 4", model: "model.4" },
        { id: 5, name: "Model 5", model: "model.5" },
        { id: 6, name: "Model 6", model: "model.6" },
        { id: 7, name: "Model 7", model: "model.7" },
        { id: 8, name: "Model 8", model: "model.8" },
        { id: 9, name: "Model 9", model: "model.9" },
        { id: 10, name: "Model 10", model: "model.10" },
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
    await mountModelSelector(["model.1", "model.2", "model.3"]);
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(3);
    const items = queryAll("li.o-autocomplete--dropdown-item");
    expect(items[0]).toHaveText("Model 1");
    expect(items[1]).toHaveText("Model 2");
    expect(items[2]).toHaveText("Model 3");
});

test("model_selector: with 8 models, showing 5", async () => {
    await mountModelSelector(
        [
            "model.1",
            "model.2",
            "model.3",
            "model.4",
            "model.5",
            "model.6",
            "model.7",
            "model.8",
        ],
        undefined,
        undefined,
        5,
    );
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(6);
    expect("li.o-autocomplete--dropdown-item:eq(5)").toHaveText("Start typing...");
});

test("model_selector: with 8 models, showing 8", async () => {
    await mountModelSelector([
        "model.1",
        "model.2",
        "model.3",
        "model.4",
        "model.5",
        "model.6",
        "model.7",
        "model.8",
    ]);
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(8);
});

test("model_selector: with more than 8 models, showing 8", async () => {
    await mountModelSelector([
        "model.1",
        "model.2",
        "model.3",
        "model.4",
        "model.5",
        "model.6",
        "model.7",
        "model.8",
        "model.9",
        "model.10",
    ]);
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(9);
    expect("li.o-autocomplete--dropdown-item:eq(8)").toHaveText("Start typing...");
});

test("model_selector: with more than 8 models, showing 9", async () => {
    await mountModelSelector(
        [
            "model.1",
            "model.2",
            "model.3",
            "model.4",
            "model.5",
            "model.6",
            "model.7",
            "model.8",
            "model.9",
            "model.10",
        ],
        undefined,
        undefined,
        9,
    );
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(10);
    expect("li.o-autocomplete--dropdown-item:eq(9)").toHaveText("Start typing...");
});

test("model_selector: with more than 8 models, showing all", async () => {
    await mountModelSelector(
        [
            "model.1",
            "model.2",
            "model.3",
            "model.4",
            "model.5",
            "model.6",
            "model.7",
            "model.8",
            "model.9",
            "model.10",
        ],
        undefined,
        undefined,
        10,
    );
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(10);
    expect("li.o-autocomplete--dropdown-item:eq(9)").toHaveText("Model 10");
});

test("model_selector: search content is not applied when opening the autocomplete", async () => {
    await mountModelSelector(["model.1", "model.2"], "_2");
    await contains(".o-autocomplete--input").click();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(2);
});

test("model_selector: with search matching some records on technical name", async () => {
    await mountModelSelector(["model.1", "model.2"]);
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--input").edit(".2", { confirm: false });
    await runAllTimers();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(1);
    expect("li.o-autocomplete--dropdown-item").toHaveText("Model 2");
});

test("model_selector: with search matching some records on business name", async () => {
    await mountModelSelector(["model.1", "model.2"]);
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--input").edit(" 2", { confirm: false });
    await runAllTimers();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(1);
    expect("li.o-autocomplete--dropdown-item").toHaveText("Model 2");
});

test("model_selector: with search matching no record", async () => {
    await mountModelSelector(["model.1", "model.2"]);
    await contains(".o-autocomplete--input").edit("a random search query", {
        confirm: false,
    });
    await runAllTimers();
    expect("li.o-autocomplete--dropdown-item").toHaveCount(1);
    expect("li.o-autocomplete--dropdown-item").toHaveText("No records");
});

test("model_selector: select a model", async () => {
    await mountModelSelector(
        ["model.1", "model.2", "model.3"],
        "Model 1",
        (selected) => {
            expect.step("model selected");
            expect(selected).toEqual({
                label: "Model 2",
                technical: "model.2",
            });
        },
    );
    await contains(".o-autocomplete--input").click();
    await contains(".o_model_selector_model_2").click();
    expect.verifySteps(["model selected"]);
});

test("model_selector: with an initial value", async () => {
    await mountModelSelector(["model.1", "model.2", "model.3"], "Model 1");
    expect(".o-autocomplete--input").toHaveValue("Model 1");
});

test("model_selector: autofocus", async () => {
    await mountWithCleanup(ModelSelector, {
        props: {
            models: ["model.1"],
            autofocus: true,
            onModelSelected: () => {},
        },
    });
    const input = queryOne("input.o-autocomplete--input");
    expect(document.activeElement).toBe(input);
});

test("models arriving after mount are loaded", async () => {
    class Parent extends Component {
        static components = { ModelSelector };
        static props = ["*"];
        static template = xml`<ModelSelector models="this.state.models" onModelSelected="() => {}"/>`;
        setup() {
            this.state = useState({ models: [] });
        }
    }
    const parent = await mountWithCleanup(Parent);
    parent.state.models = ["model.1", "model.2", "model.3"];
    await animationFrame();

    await contains(".o-autocomplete input").click();
    await runAllTimers();
    await animationFrame();
    expect(queryAll(".o-autocomplete--dropdown-item")).toHaveLength(3);
});

test("an unchanged models prop is not reloaded", async () => {
    const models = ["model.1"];
    patchWithCleanup(ModelSelector.prototype, {
        loadModels(props) {
            expect.step("loadModels");
            return super.loadModels(props);
        },
    });
    class Parent extends Component {
        static components = { ModelSelector };
        static props = ["*"];
        static template = xml`<ModelSelector models="this.models" onModelSelected="() => {}"/><span t-out="this.state.tick"/>`;
        setup() {
            this.models = models;
            this.state = useState({ tick: 0 });
        }
    }
    const parent = await mountWithCleanup(Parent);
    expect.verifySteps(["loadModels"]);

    parent.state.tick++;
    await animationFrame();
    expect.verifySteps([]);
});

test("a superseded model load does not overwrite the newer one", async () => {
    const gates = [new Deferred(), new Deferred(), new Deferred()];
    let call = 0;
    onRpc("ir.model", "display_name_for", async ({ args }) => {
        await gates[call++];
        return args[0].map((model) => ({ model, display_name: `Name ${model}` }));
    });

    /** @type {any} */
    let selector;
    class Probe extends ModelSelector {
        setup() {
            super.setup();
            selector = this;
        }
    }
    class Parent extends Component {
        static props = ["*"];
        static components = { Probe };
        static template = xml`<Probe models="this.state.models" onModelSelected="() => {}"/>`;
        setup() {
            this.state = useState({ models: ["first.model"] });
        }
    }
    gates[0].resolve();
    const parent = await mountWithCleanup(Parent);
    expect(selector.models.map((m) => m.data.technical)).toEqual(["first.model"]);

    parent.state.models = ["second.model"];
    await animationFrame();
    parent.state.models = ["third.model"];
    await animationFrame();

    gates[2].resolve();
    await animationFrame();
    gates[1].resolve();
    await animationFrame();

    expect(selector.models.map((m) => m.data.technical)).toEqual(["third.model"]);
});
