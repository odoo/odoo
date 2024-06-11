/** @odoo-module **/

import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { makeTestEnv } from "../../helpers/mock_env";
import { getFixture, mount, click, triggerEvent, editInput } from "../../helpers/utils";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";

import { Component, useState, xml } from "@odoo/owl";
import { nameService } from "@web/core/name_service";
import { dialogService } from "@web/core/dialog/dialog_service";

QUnit.module("Web Components", (hooks) => {
    QUnit.module("MultiRecordSelector");

    let target;
    const serverData = {
        models: {
            partner: {
                fields: {
                    display_name: { string: "Display name", type: "char" },
                },
                records: [
                    { id: 1, display_name: "Alice" },
                    { id: 2, display_name: "Bob" },
                    { id: 3, display_name: "Charlie" },
                ],
            },
        },
    };

    async function makeMultiRecordSelector(props, { mockRPC } = {}) {
        class Parent extends Component {
            setup() {
                this.state = useState({ resIds: props.resIds });
            }

            get recordProps() {
                return {
                    ...props,
                    resIds: this.state.resIds,
                    update: (resIds) => this._update(resIds),
                };
            }

            _update(resIds) {
                this.state.resIds = resIds;
            }
        }
        Parent.components = { MultiRecordSelector };
        Parent.template = xml`
        <MultiRecordSelector t-props="recordProps" />`;

        const env = await makeTestEnv({ serverData, mockRPC });
        await mount(Parent, target, { env });
    }

    hooks.beforeEach(async () => {
        target = getFixture();
        registry.category("services").add("hotkey", hotkeyService);
        registry.category("services").add("dialog", dialogService);
        registry.category("services").add("name", nameService);
    });

    QUnit.test("Can be renderer with no values", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [],
        });
        const input = target.querySelector(".o_multi_record_selector input");
        assert.strictEqual(input.value, "", "The input should be empty");
        assert.hasClass(input, "o_input");
    });

    QUnit.test("Can be renderer with a value", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [1],
        });
        const input = target.querySelector(".o_multi_record_selector input");
        assert.strictEqual(input.value, "");
        assert.strictEqual(target.querySelectorAll(".o_tag").length, 1);
        assert.strictEqual(target.querySelector(".o_tag").textContent, "Alice");
    });

    QUnit.test("Can be renderer with multiple values", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [1, 2],
        });
        const input = target.querySelector(".o_multi_record_selector input");
        assert.strictEqual(input.value, "");
        assert.strictEqual(target.querySelectorAll(".o_tag").length, 2);
        assert.deepEqual(
            [...target.querySelectorAll(".o_tag")].map((el) => el.textContent),
            ["Alice", "Bob"]
        );
    });

    QUnit.test("Can be updated from autocomplete", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [],
        });
        const input = target.querySelector(".o_multi_record_selector input");
        assert.containsNone(target, ".o_tag");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        await click(input);
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        const secondItem = target.querySelectorAll("li.o-autocomplete--dropdown-item")[1];
        await click(secondItem);
        assert.containsOnce(target, ".o_tag");
        assert.strictEqual(target.querySelector(".o_tag").textContent, "Bob");
    });

    QUnit.test("Display name is correctly fetched", async (assert) => {
        await makeMultiRecordSelector(
            {
                resModel: "partner",
                resIds: [1],
            },
            {
                mockRPC: (route, args) => {
                    if (args.method === "web_search_read") {
                        assert.step("web_search_read");
                        assert.strictEqual(args.model, "partner");
                        assert.deepEqual(args.kwargs.domain, [["id", "in", [1]]]);
                    }
                },
            }
        );
        assert.strictEqual(target.querySelectorAll(".o_tag").length, 1);
        assert.strictEqual(target.querySelector(".o_tag").textContent, "Alice");
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("Can give domain and context props for the name search", async (assert) => {
        await makeMultiRecordSelector(
            {
                resModel: "partner",
                resIds: [1],
                domain: [["display_name", "=", "Bob"]],
                context: { blip: "blop " },
            },
            {
                mockRPC: (route, args) => {
                    if (args.method === "name_search") {
                        assert.step("name_search");
                        assert.strictEqual(args.model, "partner");
                        assert.deepEqual(args.kwargs.args, [
                            "&",
                            ["display_name", "=", "Bob"],
                            "!",
                            ["id", "in", [1]],
                        ]);
                        assert.strictEqual(args.kwargs.context.blip, "blop ");
                    }
                },
            }
        );
        const input = target.querySelector(".o_multi_record_selector input");
        assert.verifySteps([]);
        await click(input);
        assert.verifySteps(["name_search"]);
    });

    QUnit.test("Support placeholder", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [],
            placeholder: "Select a partner",
        });
        const input = target.querySelector(".o_multi_record_selector input");
        assert.strictEqual(input.placeholder, "Select a partner");
        await click(input);
        const firstItem = target.querySelectorAll("li.o-autocomplete--dropdown-item")[0];
        await click(firstItem);
        assert.strictEqual(input.placeholder, "");
    });

    QUnit.test("Placeholder is not set if values are selected", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [1],
            placeholder: "Select a partner",
        });
        const input = target.querySelector(".o_multi_record_selector input");
        assert.strictEqual(input.placeholder, "");
    });

    QUnit.test("Can delete a tag with Backspace", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [1, 2],
        });
        await triggerEvent(target, ".o-autocomplete input", "keydown", { key: "Backspace" });
        assert.strictEqual(target.querySelectorAll(".o_tag").length, 1);
        assert.strictEqual(target.querySelector(".o_tag").textContent, "Alice");
    });

    QUnit.test("Can focus tags with arrow right and left", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [1, 2],
        });
        target.querySelector(".o-autocomplete input").focus();
        await triggerEvent(document.activeElement, "", "keydown", { key: "arrowleft" });
        assert.strictEqual(document.activeElement.textContent, "Bob");
        await triggerEvent(document.activeElement, "", "keydown", { key: "arrowleft" });
        assert.strictEqual(document.activeElement.textContent, "Alice");
        await triggerEvent(document.activeElement, "", "keydown", { key: "arrowleft" });
        assert.hasClass(document.activeElement, "o-autocomplete--input");
        await triggerEvent(document.activeElement, "", "keydown", { key: "arrowright" });
        assert.strictEqual(document.activeElement.textContent, "Alice");
        await triggerEvent(document.activeElement, "", "keydown", { key: "arrowright" });
        assert.strictEqual(document.activeElement.textContent, "Bob");
        await triggerEvent(document.activeElement, "", "keydown", { key: "arrowright" });
        assert.hasClass(document.activeElement, "o-autocomplete--input");
    });

    QUnit.test("Delete the focused element", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [1, 2],
        });
        target.querySelector(".o-autocomplete input").focus();
        await triggerEvent(document.activeElement, "", "keydown", { key: "arrowright" });
        assert.strictEqual(document.activeElement.textContent, "Alice");
        await triggerEvent(document.activeElement, "", "keydown", { key: "Backspace" });
        assert.strictEqual(target.querySelectorAll(".o_tag").length, 1);
        assert.strictEqual(target.querySelector(".o_tag").textContent, "Bob");
    });

    QUnit.test("Backspace do nothing when the input is currently edited", async (assert) => {
        await makeMultiRecordSelector({
            resModel: "partner",
            resIds: [1, 2],
        });
        target.querySelector(".o-autocomplete input").focus();
        await editInput(target, ".o-autocomplete input", "a");
        assert.strictEqual(document.activeElement.value, "a");
        await triggerEvent(document.activeElement, "", "keydown", { key: "Backspace" });
        assert.strictEqual(target.querySelectorAll(".o_tag").length, 2);
    });
});
