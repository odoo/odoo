/** @odoo-module alias=@web/../tests/core/record_selectors/record_selector_tests default=false */

import { RecordSelector } from "@web/core/record_selectors/record_selector";
import { makeTestEnv } from "../../helpers/mock_env";
import { getFixture, mount, click } from "../../helpers/utils";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";

import { Component, useState, xml } from "@odoo/owl";
import { nameService } from "@web/core/name_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { viewService } from "@web/views/view_service";
import { popoverService } from "@web/core/popover/popover_service";

QUnit.module("Web Components", (hooks) => {
    QUnit.module("RecordSelector");

    let target;
    let serverData;

    async function makeRecordSelector(props, { mockRPC } = {}) {
        class Parent extends Component {
            static components = { RecordSelector, MainComponentsContainer };
            static template = xml`
                <MainComponentsContainer />
                <RecordSelector t-props="recordProps" />`;
            static props = ["*"];
            setup() {
                this.state = useState({ resId: props.resId });
            }

            get recordProps() {
                return {
                    ...props,
                    resId: this.state.resId,
                    update: (resId) => this._update(resId),
                };
            }

            _update(resId) {
                this.state.resId = resId;
            }
        }

        const env = await makeTestEnv({ serverData, mockRPC });
        await mount(Parent, target, { env });
    }

    hooks.beforeEach(async () => {
        serverData = {
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
        target = getFixture();
        registry.category("services").add("hotkey", hotkeyService);
        registry.category("services").add("dialog", dialogService);
        registry.category("services").add("name", nameService);
    });

    QUnit.test("Can be renderer with no values", async (assert) => {
        await makeRecordSelector({
            resModel: "partner",
            resId: false,
        });
        const input = target.querySelector(".o_record_selector input");
        assert.strictEqual(input.value, "", "The input should be empty");
        assert.hasClass(input, "o_input");
    });

    QUnit.test("Can be renderer with a value", async (assert) => {
        await makeRecordSelector({
            resModel: "partner",
            resId: 1,
        });
        const input = target.querySelector(".o_record_selector input");
        assert.strictEqual(input.value, "Alice");
    });

    QUnit.test("Can be updated from autocomplete", async (assert) => {
        await makeRecordSelector({
            resModel: "partner",
            resId: 1,
        });
        const input = target.querySelector(".o_record_selector input");
        assert.strictEqual(input.value, "Alice");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        await click(input);
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        const secondItem = target.querySelectorAll("li.o-autocomplete--dropdown-item")[1];
        await click(secondItem);
        assert.strictEqual(input.value, "Bob");
    });

    QUnit.test("Display name is correctly fetched", async (assert) => {
        await makeRecordSelector(
            {
                resModel: "partner",
                resId: 1,
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
        const input = target.querySelector(".o_record_selector input");
        assert.strictEqual(input.value, "Alice");
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("Can give domain and context props for the name search", async (assert) => {
        await makeRecordSelector(
            {
                resModel: "partner",
                resId: 1,
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
                            ["id", "in", []],
                        ]);
                        assert.strictEqual(args.kwargs.context.blip, "blop ");
                    }
                },
            }
        );
        const input = target.querySelector(".o_record_selector input");
        assert.strictEqual(input.value, "Alice");
        assert.verifySteps([]);
        await click(input);
        assert.verifySteps(["name_search"]);
    });

    QUnit.test("Support placeholder", async (assert) => {
        await makeRecordSelector({
            resModel: "partner",
            resId: false,
            placeholder: "Select a partner",
        });
        const input = target.querySelector(".o_record_selector input");
        assert.strictEqual(input.placeholder, "Select a partner");
    });

    QUnit.test("domain is passed to search more", async (assert) => {
        serverData.models.partner.records = [...new Array(10)].map((el, i) => {
            return {
                id: i + 1,
                display_name: `a_${i + 1}`,
            };
        });
        serverData.views = {
            "partner,false,list": `<tree><field name="display_name" /></tree>`,
            "partner,false,search": "<search />",
        };

        const fakeService = {
            start() {},
        };
        registry.category("services").add("view", viewService);
        registry.category("services").add("action", {
            start() {
                return { doAction: () => {} };
            },
        });
        registry.category("services").add("field", fakeService);
        registry.category("services").add("company", {
            start() {
                return { currentCompany: {} };
            },
        });
        registry.category("services").add("notification", fakeService);
        registry.category("services").add("popover", popoverService);

        await makeRecordSelector(
            {
                resModel: "partner",
                resId: false,
                domain: [["display_name", "!=", "some name"]],
                placeholder: "Select a partner",
            },
            {
                mockRPC: (route, args) => {
                    if (args.method === "has_group") {
                        return true;
                    }
                    if (args.method === "web_search_read") {
                        assert.step("web_search_read");
                        assert.deepEqual(args.kwargs.domain, [
                            "&",
                            ["display_name", "!=", "some name"],
                            "!",
                            ["id", "in", []],
                        ]);
                    }
                },
            }
        );
        await click(target, ".o-autocomplete--input.o_input");
        await click(target, ".o_m2o_dropdown_option a");
        assert.containsOnce(target, ".modal .o_list_view");
        assert.verifySteps(["web_search_read"]);
    });
});
