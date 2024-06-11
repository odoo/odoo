/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { ModelSelector } from "@web/core/model_selector/model_selector";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, editInput, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";

registry.category("mock_server").add("ir.model/display_name_for", function (route, args) {
    const models = args.args[0];
    const records = this.models["ir.model"].records.filter((record) =>
        models.includes(record.model)
    );
    return records.map((record) => ({
        model: record.model,
        display_name: record.name,
    }));
});

const serviceRegistry = registry.category("services");

let env;
let fixture;

async function mountModelSelector(models = [], value = undefined, onModelSelected = () => {}) {
    await mount(ModelSelector, fixture, {
        env,
        props: {
            models,
            value,
            onModelSelected,
        },
    });
}

async function openAutocomplete(search = undefined) {
    await click(fixture, ".o-autocomplete--input");
}

async function beforeEach() {
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("orm", ormService);
    env = await makeTestEnv({
        serverData: {
            models: {
                "ir.model": {
                    fields: {
                        name: { string: "Model Name", type: "char" },
                        model: { string: "Model", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "Model 1",
                            model: "model_1",
                        },
                        {
                            id: 2,
                            name: "Model 2",
                            model: "model_2",
                        },
                        {
                            id: 3,
                            name: "Model 3",
                            model: "model_3",
                        },
                        {
                            id: 4,
                            name: "Model 4",
                            model: "model_4",
                        },
                        {
                            id: 5,
                            name: "Model 5",
                            model: "model_5",
                        },
                        {
                            id: 6,
                            name: "Model 6",
                            model: "model_6",
                        },
                        {
                            id: 7,
                            name: "Model 7",
                            model: "model_7",
                        },
                        {
                            id: 8,
                            name: "Model 8",
                            model: "model_8",
                        },
                        {
                            id: 9,
                            name: "Model 9",
                            model: "model_9",
                        },
                        {
                            id: 10,
                            name: "Model 10",
                            model: "model_10",
                        },
                    ],
                },
            },
        },
    });
    fixture = getFixture();
    patchWithCleanup(browser, {
        setTimeout: (fn) => fn(),
    });
}

QUnit.module("web > model_selector", { beforeEach });

QUnit.test("model_selector: with no model", async function (assert) {
    await mountModelSelector();
    await openAutocomplete();
    assert.containsOnce(fixture, "li.o-autocomplete--dropdown-item");
    assert.strictEqual(
        fixture.querySelector("li.o-autocomplete--dropdown-item").innerText,
        "No records"
    );
});

QUnit.test("model_selector: displays model display names", async function (assert) {
    await mountModelSelector(["model_1", "model_2", "model_3"]);
    await openAutocomplete();
    assert.containsN(fixture, "li.o-autocomplete--dropdown-item", 3);
    const items = fixture.querySelectorAll("li.o-autocomplete--dropdown-item");
    assert.strictEqual(items[0].innerText, "Model 1");
    assert.strictEqual(items[1].innerText, "Model 2");
    assert.strictEqual(items[2].innerText, "Model 3");
});

QUnit.test("model_selector: with 8 models", async function (assert) {
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
    await openAutocomplete();
    assert.containsN(fixture, "li.o-autocomplete--dropdown-item", 8);
});

QUnit.test("model_selector: with more than 8 models", async function (assert) {
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
    await openAutocomplete();
    assert.containsN(fixture, "li.o-autocomplete--dropdown-item", 9);
    assert.strictEqual(
        fixture.querySelectorAll("li.o-autocomplete--dropdown-item")[8].innerText,
        "Start typing..."
    );
});

QUnit.test(
    "model_selector: search content is not applied when opening the autocomplete",
    async function (assert) {
        await mountModelSelector(["model_1", "model_2"], "_2");
        await openAutocomplete();
        assert.containsN(fixture, "li.o-autocomplete--dropdown-item", 2);
    }
);

QUnit.test(
    "model_selector: with search matching some records on technical name",
    async function (assert) {
        await mountModelSelector(["model_1", "model_2"]);
        await openAutocomplete();
        await editInput(fixture, ".o-autocomplete--input", "_2");
        assert.containsOnce(fixture, "li.o-autocomplete--dropdown-item");
        assert.strictEqual(
            fixture.querySelector("li.o-autocomplete--dropdown-item").innerText,
            "Model 2"
        );
    }
);

QUnit.test(
    "model_selector: with search matching some records on business name",
    async function (assert) {
        await mountModelSelector(["model_1", "model_2"]);
        await openAutocomplete();
        await editInput(fixture, ".o-autocomplete--input", " 2");
        assert.containsOnce(fixture, "li.o-autocomplete--dropdown-item");
        assert.strictEqual(
            fixture.querySelector("li.o-autocomplete--dropdown-item").innerText,
            "Model 2"
        );
    }
);

QUnit.test("model_selector: with search matching no record", async function (assert) {
    await mountModelSelector(["model_1", "model_2"]);
    await openAutocomplete("a random search query");
    await editInput(fixture, ".o-autocomplete--input", "a random search query");
    assert.containsOnce(fixture, "li.o-autocomplete--dropdown-item");
    assert.strictEqual(
        fixture.querySelector("li.o-autocomplete--dropdown-item").innerText,
        "No records"
    );
});

QUnit.test("model_selector: select a model", async function (assert) {
    await mountModelSelector(["model_1", "model_2", "model_3"], "Model 1", (selected) => {
        assert.step("model selected");
        assert.deepEqual(selected, {
            label: "Model 2",
            technical: "model_2",
        });
    });
    await openAutocomplete();
    await click(fixture.querySelector(".o_model_selector_model_2"));
    assert.verifySteps(["model selected"]);
});

QUnit.test("model_selector: click on start typing", async function (assert) {
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
    await openAutocomplete();
    await click(fixture.querySelectorAll("li.o-autocomplete--dropdown-item")[8]);
    assert.equal(fixture.querySelector(".o-autocomplete--input").value, "");
    assert.equal(fixture.querySelector(".o-autocomplete.dropdown ul"), null);

    //label must be empty
    assert.equal(fixture.querySelector(".o_global_filter_label"), null);

    //Default value and matching fields should not be available
    assert.equal(fixture.querySelector(".o_side_panel_section"), null);
});

QUnit.test("model_selector: with an initial value", async function (assert) {
    await mountModelSelector(["model_1", "model_2", "model_3"], "Model 1");
    assert.equal(fixture.querySelector(".o-autocomplete--input").value, "Model 1");
});
