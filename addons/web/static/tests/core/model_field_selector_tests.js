/** @odoo-module **/

import { Component, useState, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { fieldService } from "@web/core/field_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import {
    click,
    editInput,
    getFixture,
    getNodesTextContent,
    mount,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "../helpers/utils";

let target;
let serverData;

async function mountComponent(Component, params = {}) {
    const env = await makeTestEnv({ serverData, mockRPC: params.mockRPC });
    await mount(MainComponentsContainer, target, { env });
    return mount(Component, target, { env, props: params.props || {} });
}

export async function openModelFieldSelectorPopover(target, index = 0) {
    const el = target.querySelectorAll(".o_model_field_selector")[index];
    await click(el);
}

function getDisplayedFieldNames(target) {
    return getNodesTextContent(
        target.querySelectorAll(".o_model_field_selector_popover_item_name")
    );
}

export function getModelFieldSelectorValues(target) {
    return getNodesTextContent(target.querySelectorAll("span.o_model_field_selector_chain_part"));
}

function getTitle(target) {
    return target.querySelector(
        ".o_model_field_selector_popover .o_model_field_selector_popover_title"
    ).innerText;
}

async function clickPrev(target) {
    await click(target, ".o_model_field_selector_popover_prev_page");
}

async function followRelation(target, index = 0) {
    await click(target.querySelectorAll(".o_model_field_selector_popover_item_relation")[index]);
}

function getFocusedFieldName(target) {
    return target.querySelector(".o_model_field_selector_popover_item.active").innerText;
}

function addProperties() {
    serverData.models.partner.fields.properties = {
        string: "Properties",
        type: "properties",
        definition_record: "product_id",
        definition_record_field: "definitions",
        searchable: true,
    };
    serverData.models.product.fields.definitions = {
        string: "Definitions",
        type: "properties_definition",
    };
    serverData.models.product.records[0].definitions = [
        { name: "xphone_prop_1", string: "P1", type: "boolean" },
        { name: "xphone_prop_2", string: "P2", type: "char" },
    ];
    serverData.models.product.records[1].definitions = [
        { name: "xpad_prop_1", string: "P1", type: "date" },
    ];
}

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: { string: "Foo", type: "char", searchable: true },
                        bar: { string: "Bar", type: "boolean", searchable: true },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                        json_field: {
                            string: "Json field",
                            type: "json",
                            searchable: true,
                        },
                    },
                    records: [
                        { id: 1, foo: "yop", bar: true, product_id: 37 },
                        { id: 2, foo: "blip", bar: true, product_id: false },
                        { id: 4, foo: "abc", bar: false, product_id: 41 },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        { id: 37, display_name: "xphone" },
                        { id: 41, display_name: "xpad" },
                    ],
                },
            },
        };

        registry.category("services").add("popover", popoverService);
        registry.category("services").add("orm", ormService);
        registry.category("services").add("localization", makeFakeLocalizationService());
        registry.category("services").add("ui", uiService);
        registry.category("services").add("field", fieldService);
        registry.category("services").add("hotkey", hotkeyService);

        target = getFixture();
    });

    QUnit.module("ModelFieldSelector");

    QUnit.test("creating a field chain from scratch", async (assert) => {
        function getValueFromDOM(el) {
            return [...el.querySelectorAll(".o_model_field_selector_chain_part")]
                .map((part) => part.textContent.trim())
                .join(" -> ");
        }
        class Parent extends Component {
            setup() {
                this.path = "";
            }
            onUpdate(path) {
                assert.step(`update: ${path}`);
                this.path = path;
                this.render();
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                path="path"
                isDebugMode="false"
                update="(path) => this.onUpdate(path)"
            />
        `;

        const fieldSelector = await mountComponent(Parent);

        await openModelFieldSelectorPopover(target);
        assert.strictEqual(
            target.querySelector("input.o_input[placeholder='Search...']"),
            document.activeElement
        );
        assert.containsOnce(target, ".o_model_field_selector_popover");

        // The field selector popover should contain the list of "partner"
        // fields. "Bar" should be among them.
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_popover_item_name").textContent,
            "Bar"
        );

        // Clicking the "Bar" field should close the popover and set the field
        // chain to "bar" as it is a basic field
        await click(target.querySelector(".o_model_field_selector_popover_item_name"));
        assert.containsNone(target, ".o_model_field_selector_popover");
        assert.strictEqual(getValueFromDOM(target), "Bar");
        assert.strictEqual(fieldSelector.path, "bar");
        assert.verifySteps(["update: bar"]);

        await openModelFieldSelectorPopover(target);
        assert.containsOnce(target, ".o_model_field_selector_popover");
        // The field selector popover should contain the list of "partner"
        // fields. "Product" should be among them.
        assert.containsOnce(
            target,
            ".o_model_field_selector_popover .o_model_field_selector_popover_relation_icon",
            "field selector popover should contain the 'Product' field"
        );

        // Clicking on the "Product" field should update the popover to show
        // the product fields (so only "Product Name" should be there)
        await click(
            target.querySelector(
                ".o_model_field_selector_popover .o_model_field_selector_popover_relation_icon"
            )
        );
        assert.containsOnce(target, ".o_model_field_selector_popover_item_name");
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_popover_item_name").textContent,
            "Product Name",
            "the name of the only suggestion should be 'Product Name'"
        );

        await click(target.querySelector(".o_model_field_selector_popover_item_name"));
        assert.containsNone(target, ".o_model_field_selector_popover");
        assert.strictEqual(getValueFromDOM(target), "Product -> Product Name");
        assert.verifySteps(["update: product_id.name"]);

        // Remove the current selection and recreate it again
        await openModelFieldSelectorPopover(target);
        await click(target, ".o_model_field_selector_popover_prev_page");
        await click(target, ".o_model_field_selector_popover_close");
        assert.verifySteps(["update: product_id"]);

        await openModelFieldSelectorPopover(target);
        assert.containsOnce(
            target,
            ".o_model_field_selector_popover .o_model_field_selector_popover_relation_icon"
        );

        await click(
            target.querySelector(
                ".o_model_field_selector_popover .o_model_field_selector_popover_relation_icon"
            )
        );
        await click(target.querySelector(".o_model_field_selector_popover_item_name"));
        assert.containsNone(target, ".o_model_field_selector_popover");
        assert.strictEqual(getValueFromDOM(target), "Product -> Product Name");
        assert.verifySteps(["update: product_id.name"]);
    });

    QUnit.test("default field chain should set the page data correctly", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                path: "product_id",
                resModel: "partner",
                isDebugMode: false,
            },
        });
        await openModelFieldSelectorPopover(target);
        assert.containsOnce(target, ".o_model_field_selector_popover");
        assert.deepEqual(getDisplayedFieldNames(target), ["Bar", "Foo", "Product"]);
        assert.hasClass(
            target.querySelectorAll(".o_model_field_selector_popover_item:nth-child(3)"),
            "active"
        );
    });

    QUnit.test("use the filter option", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                path: "",
                resModel: "partner",
                filter: (field) => field.type === "many2one" && field.searchable,
            },
        });
        await openModelFieldSelectorPopover(target);
        assert.deepEqual(getDisplayedFieldNames(target), ["Product"]);
    });

    QUnit.test("default `showSearchInput` option", async (assert) => {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });

        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                path: "",
                resModel: "partner",
            },
        });
        await openModelFieldSelectorPopover(target);
        assert.containsOnce(
            target,
            ".o_model_field_selector_popover .o_model_field_selector_popover_search"
        );
        assert.deepEqual(getDisplayedFieldNames(target), ["Bar", "Foo", "Product"]);

        // search 'xx'
        await editInput(
            target,
            ".o_model_field_selector_popover .o_model_field_selector_popover_search input",
            "xx"
        );
        assert.deepEqual(getDisplayedFieldNames(target), []);

        // search 'Pro'
        await editInput(
            target,
            ".o_model_field_selector_popover .o_model_field_selector_popover_search input",
            "Pro"
        );
        assert.deepEqual(getDisplayedFieldNames(target), ["Product"]);
    });

    QUnit.test("false `showSearchInput` option", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                showSearchInput: false,
                path: "",
                resModel: "partner",
            },
        });
        await openModelFieldSelectorPopover(target);
        assert.containsNone(
            target,
            ".o_model_field_selector_popover .o_model_field_selector_popover_search"
        );
    });

    QUnit.test("create a field chain with value 1 i.e. TRUE_LEAF", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                showSearchInput: false,
                path: 1,
                resModel: "partner",
            },
        });
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_chain_part").textContent.trim(),
            "1"
        );
    });

    QUnit.test("create a field chain with value 0 i.e. FALSE_LEAF", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                showSearchInput: false,
                path: 0,
                resModel: "partner",
            },
        });
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_chain_part").textContent.trim(),
            "0",
            "field name value should be 0."
        );
    });

    QUnit.test("cache fields_get", async (assert) => {
        serverData.models.partner.fields.partner_id = {
            string: "Partner",
            type: "many2one",
            relation: "partner",
            searchable: true,
        };

        await mountComponent(ModelFieldSelector, {
            mockRPC(_, { method }) {
                if (method === "fields_get") {
                    assert.step("fields_get");
                }
            },
            props: {
                readonly: false,
                path: "partner_id.partner_id.partner_id.foo",
                resModel: "partner",
            },
        });
        assert.verifySteps(["fields_get"]);
    });

    QUnit.test("Using back button in popover", async (assert) => {
        serverData.models.partner.fields.partner_id = {
            string: "Partner",
            type: "many2one",
            relation: "partner",
            searchable: true,
        };

        class Parent extends Component {
            setup() {
                this.path = "partner_id.foo";
            }
            onUpdate(path) {
                this.path = path;
                this.render();
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                path="path"
                update="(path) => this.onUpdate(path)"
            />
        `;

        await mountComponent(Parent);
        assert.deepEqual(getModelFieldSelectorValues(target), ["Partner", "Foo"]);
        assert.containsNone(target, ".o_model_field_selector i.o_model_field_selector_warning");

        await openModelFieldSelectorPopover(target);
        await click(target, ".o_model_field_selector_popover_prev_page");
        assert.deepEqual(getModelFieldSelectorValues(target), ["Partner"]);
        assert.containsNone(target, ".o_model_field_selector i.o_model_field_selector_warning");

        await click(
            target,
            ".o_model_field_selector_popover_item:nth-child(1) .o_model_field_selector_popover_item_name"
        );
        assert.deepEqual(getModelFieldSelectorValues(target), ["Bar"]);
        assert.containsNone(target, ".o_model_field_selector_popover");
    });

    QUnit.test("select a relational field does not follow relation", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                path: "",
                resModel: "partner",
                update(path) {
                    assert.step(path);
                },
            },
        });
        await openModelFieldSelectorPopover(target);
        assert.containsOnce(
            target,
            ".o_model_field_selector_popover_item:last-child .o_model_field_selector_popover_relation_icon"
        );

        await click(
            target,
            ".o_model_field_selector_popover_item:last-child .o_model_field_selector_popover_item_name"
        );
        assert.verifySteps(["product_id"]);
        assert.containsNone(target, ".o_popover");

        await openModelFieldSelectorPopover(target);
        assert.deepEqual(getDisplayedFieldNames(target), ["Bar", "Foo", "Product"]);
        assert.containsOnce(target, ".o_model_field_selector_popover_relation_icon");

        await click(target, ".o_model_field_selector_popover_relation_icon");
        assert.deepEqual(getDisplayedFieldNames(target), ["Product Name"]);
        assert.containsOnce(target, ".o_popover");

        await click(target, ".o_model_field_selector_popover_item_name");
        assert.verifySteps(["product_id.name"]);
        assert.containsNone(target, ".o_popover");
    });

    QUnit.test("can follow relations", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                path: "",
                resModel: "partner",
                followRelations: true, // default
                update(path) {
                    assert.strictEqual(path, "product_id");
                },
            },
        });
        await openModelFieldSelectorPopover(target);
        assert.deepEqual(getDisplayedFieldNames(target), ["Bar", "Foo", "Product"]);
        assert.containsOnce(target, ".o_model_field_selector_popover_relation_icon");

        await click(target, ".o_model_field_selector_popover_relation_icon");
        assert.deepEqual(getDisplayedFieldNames(target), ["Product Name"]);
        assert.containsOnce(target, ".o_popover");
    });

    QUnit.test("cannot follow relations", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                path: "",
                resModel: "partner",
                followRelations: false,
                update(path) {
                    assert.strictEqual(path, "product_id");
                },
            },
        });
        await openModelFieldSelectorPopover(target);
        assert.deepEqual(getDisplayedFieldNames(target), ["Bar", "Foo", "Product"]);
        assert.containsNone(target, ".o_model_field_selector_popover_relation_icon");

        await click(
            target,
            ".o_model_field_selector_popover_item:nth-child(3) .o_model_field_selector_popover_item_name"
        );
        assert.containsNone(target, ".o_popover");
        assert.deepEqual(getModelFieldSelectorValues(target), ["Product"]);
    });

    QUnit.test("Edit path in popover debug input", async (assert) => {
        serverData.models.partner.fields.partner_id = {
            string: "Partner",
            type: "many2one",
            relation: "partner",
            searchable: true,
        };

        class Parent extends Component {
            setup() {
                this.path = "foo";
            }
            onUpdate(path) {
                this.path = path;
                this.render();
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`
                    <ModelFieldSelector
                        readonly="false"
                        resModel="'partner'"
                        path="path"
                        isDebugMode="true"
                        update="(pathInfo) => this.onUpdate(pathInfo)"
                    />
                `;

        await mountComponent(Parent);
        assert.deepEqual(getModelFieldSelectorValues(target), ["Foo"]);

        await openModelFieldSelectorPopover(target);
        await editInput(
            target,
            ".o_model_field_selector_popover .o_model_field_selector_debug",
            "partner_id.bar"
        );
        assert.deepEqual(getModelFieldSelectorValues(target), ["Partner", "Bar"]);
    });

    QUnit.test("title on first four pages", async (assert) => {
        serverData.models.turtle = {
            fields: {
                mother_id: {
                    string: "Mother",
                    type: "many2one",
                    relation: "turtle",
                    searchable: true,
                },
            },
        };

        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                path: "mother_id",
                resModel: "turtle",
            },
        });
        await openModelFieldSelectorPopover(target);
        assert.strictEqual(getTitle(target), "");

        await followRelation(target);
        assert.strictEqual(getTitle(target), "Mother");

        await followRelation(target);
        assert.strictEqual(getTitle(target), "... > Mother");

        await followRelation(target);
        assert.strictEqual(getTitle(target), "... > Mother");
    });

    QUnit.test("start on complex path and click prev", async (assert) => {
        serverData.models.turtle = {
            fields: {
                mother_id: {
                    string: "Mother",
                    type: "many2one",
                    relation: "turtle",
                    searchable: true,
                },
                father_id: {
                    string: "Father",
                    type: "many2one",
                    relation: "turtle",
                    searchable: true,
                },
            },
        };

        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                path: "mother_id.father_id.mother_id",
                resModel: "turtle",
            },
        });

        await openModelFieldSelectorPopover(target);
        // viewing third page
        // mother is selected on that page
        assert.strictEqual(getTitle(target), "... > Father");
        assert.strictEqual(getFocusedFieldName(target), "Mother");
        assert.deepEqual(getModelFieldSelectorValues(target), ["Mother", "Father", "Mother"]);

        // select Father on third page and go to next page
        // no selection on fourth page --> first item is focused
        await followRelation(target);
        assert.strictEqual(getTitle(target), "... > Father");
        assert.strictEqual(getFocusedFieldName(target), "Father");
        assert.deepEqual(getModelFieldSelectorValues(target), ["Mother", "Father", "Father"]);

        // go back to third page. Nothing has changed
        await clickPrev(target);
        assert.strictEqual(getTitle(target), "... > Father");
        assert.strictEqual(getFocusedFieldName(target), "Father");
        assert.deepEqual(getModelFieldSelectorValues(target), ["Mother", "Father", "Father"]);

        // go back to second page. Nothing has changed.
        await clickPrev(target);
        assert.strictEqual(getTitle(target), "Mother");
        assert.strictEqual(getFocusedFieldName(target), "Father");
        assert.deepEqual(getModelFieldSelectorValues(target), ["Mother", "Father"]);

        // go back to first page. Nothing has changed.
        await clickPrev(target);
        assert.strictEqual(getTitle(target), "");
        assert.strictEqual(getFocusedFieldName(target), "Mother");
        assert.deepEqual(getModelFieldSelectorValues(target), ["Mother"]);
        assert.containsNone(target, ".o_model_field_selector_popover_prev_page");
    });

    QUnit.test("support of invalid paths (allowEmpty=false)", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({ path: `` });
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="state.path" />`;

        const parent = await mountComponent(Parent);
        assert.deepEqual(getModelFieldSelectorValues(target), ["-"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        parent.state.path = undefined;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["-"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        parent.state.path = false;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["-"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        parent.state.path = {};
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["-"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        parent.state.path = `a`;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["a"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        parent.state.path = `foo.a`;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["Foo", "a"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        parent.state.path = `a.foo`;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["a", "foo"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");
    });

    QUnit.test("support of invalid paths (allowEmpty=true)", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({ path: `` });
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="state.path" allowEmpty="true" />`;

        const parent = await mountComponent(Parent);
        assert.deepEqual(getModelFieldSelectorValues(target), []);
        assert.containsNone(target, ".o_model_field_selector_warning");

        parent.state.path = undefined;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), []);
        assert.containsNone(target, ".o_model_field_selector_warning");

        parent.state.path = false;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), []);
        assert.containsNone(target, ".o_model_field_selector_warning");

        parent.state.path = {};
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["-"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        parent.state.path = `a`;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["a"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        parent.state.path = `foo.a`;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["Foo", "a"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        parent.state.path = `a.foo`;
        await nextTick();
        assert.deepEqual(getModelFieldSelectorValues(target), ["a", "foo"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");
    });

    QUnit.test("debug input", async (assert) => {
        assert.expect(10);
        let num = 1;
        class Parent extends Component {
            setup() {
                this.state = useState({ path: `` });
            }
            update(path, fieldInfo) {
                if (num === 1) {
                    assert.strictEqual(path, "a");
                    assert.deepEqual(fieldInfo, {
                        fieldDef: null,
                        resModel: "partner",
                    });
                    num++;
                } else {
                    assert.strictEqual(path, "foo");
                    assert.deepEqual(fieldInfo, {
                        fieldDef: {
                            name: "foo",
                            searchable: true,
                            string: "Foo",
                            type: "char",
                        },
                        resModel: "partner",
                    });
                }
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" isDebugMode="true" path="state.path" update.bind="update"/>`;

        await mountComponent(Parent);
        assert.deepEqual(getModelFieldSelectorValues(target), ["-"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        await openModelFieldSelectorPopover(target);
        await editInput(target, ".o_model_field_selector_debug", "a");
        assert.deepEqual(getModelFieldSelectorValues(target), ["a"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");

        await click(target, ".o_model_field_selector_popover_close");

        await openModelFieldSelectorPopover(target);
        const debugInput = target.querySelector(".o_model_field_selector_debug");
        debugInput.focus();
        debugInput.value = "foo";
        await triggerEvent(debugInput, null, "keydown", { key: "Enter" });
        assert.deepEqual(getModelFieldSelectorValues(target), ["Foo"]);
        assert.containsNone(target, ".o_model_field_selector_warning");

        await click(target, ".o_model_field_selector_popover_close");
    });

    QUnit.test("focus on search input", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({ path: `foo` });
            }
            update() {}
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="state.path" update.bind="update"/>`;

        await mountComponent(Parent);
        await openModelFieldSelectorPopover(target);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_model_field_selector_popover_search .o_input")
        );

        await followRelation(target);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_model_field_selector_popover_search .o_input")
        );
    });

    QUnit.test("support properties", async (assert) => {
        addProperties();

        class Parent extends Component {
            static components = { ModelFieldSelector };
            static template = xml`
                <ModelFieldSelector
                    readonly="false"
                    resModel="'partner'"
                    path="path"
                    isDebugMode="true"
                    update="(path, fieldInfo) => this.onUpdate(path)"
                />
            `;
            setup() {
                this.path = "foo";
            }
            onUpdate(path) {
                this.path = path;
                assert.step(path);
                this.render();
            }
        }

        await mountComponent(Parent);
        await openModelFieldSelectorPopover(target);
        assert.strictEqual(getTitle(target), "");
        assert.containsOnce(target, ".o_model_field_selector_popover_item[data-name='properties']");
        assert.containsOnce(
            target,
            ".o_model_field_selector_popover_item[data-name='properties'] .o_model_field_selector_popover_relation_icon"
        );
        assert.deepEqual(getModelFieldSelectorValues(target), ["Foo"]);
        assert.containsNone(target, ".o_model_field_selector_warning");

        await click(
            target,
            ".o_model_field_selector_popover_item[data-name='properties'] .o_model_field_selector_popover_relation_icon",
            "click on the relation icon should open the properties page"
        );
        assert.deepEqual(getModelFieldSelectorValues(target), ["Properties"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");
        assert.verifySteps([]);

        await clickPrev(target);
        assert.strictEqual(getTitle(target), "");
        await click(
            target,
            ".o_model_field_selector_popover_item[data-name='properties'] .o_model_field_selector_popover_item_name",
            "click on the name should open the properties page"
        );
        assert.strictEqual(getTitle(target), "Properties");
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_value").textContent,
            "Properties"
        );
        assert.containsN(target, ".o_model_field_selector_popover_item", 3);
        assert.containsOnce(
            target,
            ".o_model_field_selector_popover_item[data-name='xphone_prop_1']"
        );
        assert.containsOnce(
            target,
            ".o_model_field_selector_popover_item[data-name='xphone_prop_2']"
        );
        assert.containsOnce(
            target,
            ".o_model_field_selector_popover_item[data-name='xpad_prop_1']"
        );
        assert.deepEqual(getDisplayedFieldNames(target), [
            "P1 (xphone)xphone_prop_1 (boolean)",
            "P1 (xpad)xpad_prop_1 (date)",
            "P2 (xphone)xphone_prop_2 (char)",
        ]);

        await click(
            target,
            ".o_model_field_selector_popover_item[data-name='xphone_prop_2'] .o_model_field_selector_popover_item_name"
        );
        assert.verifySteps(["properties.xphone_prop_2"]);
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_value").textContent,
            "PropertiesP2"
        );
        assert.containsNone(target, ".o_model_field_selector_warning");
    });

    QUnit.test("search on field string and name in debug mode", async (assert) => {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() }); // for debouncedSearchFields
        serverData.models.partner.fields.ucit = {
            type: "char",
            string: "Some string",
            searchable: true,
        };
        class Parent extends Component {
            static components = { ModelFieldSelector };
            static template = xml`
                <ModelFieldSelector
                    readonly="false"
                    resModel="'partner'"
                    path="'foo'"
                    isDebugMode="true"
                />
            `;
        }
        await mountComponent(Parent);
        await openModelFieldSelectorPopover(target);
        await editInput(
            target,
            ".o_model_field_selector_popover .o_model_field_selector_popover_search input",
            "uct"
        );
        assert.deepEqual(getDisplayedFieldNames(target), [
            "Productproduct_id (many2one)",
            "Some stringucit (char)",
        ]);
    });

    QUnit.test("clear button (allowEmpty=true)", async (assert) => {
        class Parent extends Component {
            static components = { ModelFieldSelector };
            static template = xml`
                <ModelFieldSelector
                    readonly="false"
                    resModel="'partner'"
                    path="path"
                    allowEmpty="true"
                    isDebugMode="true"
                    update="(path, fieldInfo) => this.onUpdate(path)"
                />
            `;
            setup() {
                this.path = "baaarrr";
            }
            onUpdate(path) {
                this.path = path;
                assert.step(`path is ${JSON.stringify(path)}`);
                this.render();
            }
        }

        await mountComponent(Parent);

        assert.deepEqual(getModelFieldSelectorValues(target), ["baaarrr"]);
        assert.containsOnce(target, ".o_model_field_selector_warning");
        assert.containsOnce(target, ".o_model_field_selector .fa.fa-times");

        // clear when popover is not open
        await click(target, ".o_model_field_selector .fa.fa-times");
        assert.deepEqual(getModelFieldSelectorValues(target), []);
        assert.containsNone(target, ".o_model_field_selector_warning");
        assert.containsNone(target, ".o_model_field_selector .fa.fa-times");
        assert.verifySteps([`path is ""`]);

        await openModelFieldSelectorPopover(target);
        await click(target.querySelector(".o_model_field_selector_popover_item_name"));
        assert.deepEqual(getModelFieldSelectorValues(target), ["Bar"]);
        assert.containsNone(target, ".o_model_field_selector_warning");
        assert.containsOnce(target, ".o_model_field_selector .fa.fa-times");
        assert.verifySteps([`path is "bar"`]);

        // clear when popover is open
        await openModelFieldSelectorPopover(target);
        await click(target, ".o_model_field_selector .fa.fa-times");
        assert.deepEqual(getModelFieldSelectorValues(target), []);
        assert.containsNone(target, ".o_model_field_selector_warning");
        assert.containsNone(target, ".o_model_field_selector .fa.fa-times");
        assert.verifySteps([`path is ""`]);
    });

    QUnit.test("Modify path in popover debug input and click away", async (assert) => {
        class Parent extends Component {
            setup() {
                this.path = "foo";
            }
            onUpdate(path) {
                this.path = path;
                assert.step(path);
                this.render();
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`
                    <ModelFieldSelector
                        readonly="false"
                        resModel="'partner'"
                        path="path"
                        isDebugMode="true"
                        update="(pathInfo) => this.onUpdate(pathInfo)"
                    />
                `;

        await mountComponent(Parent);
        assert.deepEqual(getModelFieldSelectorValues(target), ["Foo"]);

        await openModelFieldSelectorPopover(target);
        const input = target.querySelector(
            ".o_model_field_selector_popover .o_model_field_selector_debug"
        );
        input.value = "foooooo";
        await triggerEvent(input, null, "input");
        assert.deepEqual(getModelFieldSelectorValues(target), ["Foo"]);

        await click(target);
        assert.deepEqual(getModelFieldSelectorValues(target), ["foooooo"]);
        assert.verifySteps(["foooooo"]);
    });

    QUnit.test("showDebugInput = false", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                path: "product_id",
                resModel: "partner",
                isDebugMode: true,
                showDebugInput: false,
            },
        });

        await openModelFieldSelectorPopover(target);
        assert.containsNone(target, ".o_model_field_selector_debug");
    });
});
