/** @odoo-module **/

import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { viewService } from "@web/views/view_service";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, triggerEvent, mount, editInput } from "../helpers/utils";
import { makeFakeLocalizationService } from "../helpers/mock_services";

import { Component, xml } from "@odoo/owl";

let target;
let serverData;

async function mountComponent(Component, params = {}) {
    const env = await makeTestEnv({ serverData, mockRPC: params.mockRPC });
    await mount(MainComponentsContainer, target, { env });
    return mount(Component, target, { env, props: params.props || {} });
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
        registry.category("services").add("view", viewService);

        target = getFixture();
    });

    QUnit.module("ModelFieldSelector");

    QUnit.test("creating a field chain from scratch", async (assert) => {
        function getValueFromDOM(el) {
            return [...el.querySelectorAll(".o_field_selector_chain_part")]
                .map((part) => part.textContent.trim())
                .join(" -> ");
        }

        class Parent extends Component {
            setup() {
                this.fieldName = "";
            }
            onUpdate(value) {
                this.fieldName = value;
                this.render();
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                fieldName="fieldName"
                isDebugMode="false"
                update="(value) => this.onUpdate(value)"
            />
        `;

        // Create the field selector and its mock environment
        const fieldSelector = await mountComponent(Parent);

        // Focusing the field selector input should open a field selector popover
        await click(target, ".o_field_selector");
        assert.strictEqual(
            target.querySelector("input.o_input[placeholder='Search...']"),
            document.activeElement,
            "the field selector input should be focused"
        );
        assert.containsOnce(
            target,
            ".o_field_selector_popover",
            "field selector popover should be visible"
        );

        // The field selector popover should contain the list of "partner"
        // fields. "Bar" should be among them.
        assert.strictEqual(
            target.querySelector(".o_field_selector_popover .o_field_selector_item").textContent,
            "Bar",
            "field selector popover should contain the 'Bar' field"
        );

        // Clicking the "Bar" field should close the popover and set the field
        // chain to "bar" as it is a basic field
        await click(target.querySelector(".o_field_selector_popover .o_field_selector_item"));
        assert.containsNone(
            target,
            ".o_field_selector_popover",
            "field selector popover should be closed now"
        );
        assert.strictEqual(
            getValueFromDOM(target),
            "Bar",
            "field selector value should be displayed with a 'Bar' tag"
        );
        assert.strictEqual(
            fieldSelector.fieldName,
            "bar",
            "the selected field should be correctly set"
        );

        // Focusing the input again should open the same popover
        await click(target, ".o_field_selector");
        assert.containsOnce(
            target,
            ".o_field_selector_popover",
            "field selector popover should be visible"
        );

        // The field selector popover should contain the list of "partner"
        // fields. "Product" should be among them.
        assert.containsOnce(
            target,
            ".o_field_selector_popover .o_field_selector_relation_icon",
            "field selector popover should contain the 'Product' field"
        );

        // Clicking on the "Product" field should update the popover to show
        // the product fields (so only "Product Name" should be there)
        await click(
            target.querySelector(".o_field_selector_popover .o_field_selector_relation_icon")
        );
        assert.containsOnce(
            target,
            ".o_field_selector_popover .o_field_selector_item",
            "there should be only one field proposition for 'product' model"
        );
        assert.strictEqual(
            target.querySelector(".o_field_selector_popover .o_field_selector_item").textContent,
            "Product Name",
            "the name of the only suggestion should be 'Product Name'"
        );

        // Clicking on "Product Name" should close the popover and set the chain
        // to "product_id.name"
        await click(target.querySelector(".o_field_selector_popover .o_field_selector_item"));
        assert.containsNone(
            target,
            ".o_field_selector_popover",
            "field selector popover should be closed now"
        );
        assert.strictEqual(
            getValueFromDOM(target),
            "Product -> Product Name",
            "field selector value should be displayed with two tags: 'Product' and 'Product Name'"
        );

        // Remove the current selection and recreate it again
        await click(target, ".o_field_selector");
        await click(target, ".o_field_selector_prev_page");
        await click(target, ".o_field_selector_prev_page");
        await click(target, ".o_field_selector_close");

        await click(target, ".o_field_selector");
        assert.containsOnce(
            target,
            ".o_field_selector_popover .o_field_selector_relation_icon",
            "field selector popover should contain the 'Product' field"
        );

        await click(
            target.querySelector(".o_field_selector_popover .o_field_selector_relation_icon")
        );
        await click(target.querySelector(".o_field_selector_popover .o_field_selector_item"));
        assert.containsNone(
            target,
            ".o_field_selector_popover",
            "field selector popover should be closed now"
        );
        assert.strictEqual(
            getValueFromDOM(target),
            "Product -> Product Name",
            "field selector value should be displayed with two tags: 'Product' and 'Product Name'"
        );
    });

    QUnit.test("default field chain should set the page data correctly", async (assert) => {
        assert.expect(3);

        // Create the field selector and its mock environment
        // passing 'product_id' as a prefilled field-chain
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                fieldName: "product_id",
                resModel: "partner",
                isDebugMode: false,
            },
        });

        // Focusing the field selector input should open a field selector popover
        await click(target, ".o_field_selector");
        assert.containsOnce(
            target,
            ".o_field_selector_popover",
            "field selector popover should be visible"
        );

        // The field selector popover should contain the list of "product"
        // fields. "Product Name" should be among them.
        assert.containsOnce(
            target,
            ".o_field_selector_popover .o_field_selector_item",
            "there should be only one field proposition for 'product' model"
        );
        assert.strictEqual(
            target.querySelector(".o_field_selector_popover .o_field_selector_item").textContent,
            "Product Name",
            "the name of the only suggestion should be 'Product Name'"
        );
    });

    QUnit.test("use the filter option", async (assert) => {
        assert.expect(2);

        // Create the field selector and its mock environment
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                fieldName: "",
                resModel: "partner",
                filter: (field) => field.type === "many2one",
            },
        });

        await click(target, ".o_field_selector");
        assert.containsOnce(
            target,
            ".o_field_selector_popover .o_field_selector_item",
            "there should only be one element"
        );
        assert.strictEqual(
            target.querySelector(".o_field_selector_popover .o_field_selector_page").textContent,
            "Product",
            "the available field should be the many2one"
        );
    });

    QUnit.test("default `showSearchInput` option", async (assert) => {
        assert.expect(6);

        // Create the field selector and its mock environment
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                fieldName: "",
                resModel: "partner",
            },
        });

        await click(target, ".o_field_selector");
        assert.containsOnce(
            target,
            ".o_field_selector_popover .o_field_selector_search",
            "there should be a search input"
        );

        // without search
        assert.containsN(
            target,
            ".o_field_selector_popover .o_field_selector_item",
            3,
            "there should be three available fields"
        );
        assert.strictEqual(
            target.querySelector(".o_field_selector_popover .o_field_selector_page").textContent,
            "BarFooProduct",
            "the available field should be correct"
        );

        const input = target.querySelector(
            ".o_field_selector_popover .o_field_selector_search input"
        );
        input.value = "xx";
        await triggerEvent(input, null, "input");
        assert.containsNone(
            target,
            ".o_field_selector_popover .o_field_selector_item",
            "there shouldn't be any element"
        );

        input.value = "Pro";
        await triggerEvent(input, null, "input");
        assert.containsOnce(
            target,
            ".o_field_selector_popover .o_field_selector_item",
            "there should only be one element"
        );
        assert.strictEqual(
            target.querySelector(".o_field_selector_popover .o_field_selector_page").textContent,
            "Product",
            "the available field should be the Product"
        );
    });

    QUnit.test("false `showSearchInput` option", async (assert) => {
        assert.expect(1);

        // Create the field selector and its mock environment
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                showSearchInput: false,
                fieldName: "",
                resModel: "partner",
            },
        });

        await click(target, ".o_field_selector");
        assert.containsNone(
            target,
            ".o_field_selector_popover .o_field_selector_search",
            "there should be no search input"
        );
    });

    QUnit.test("create a field chain with value 1 i.e. TRUE_LEAF", async (assert) => {
        assert.expect(1);

        //create the field selector with domain value ["1"]
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                showSearchInput: false,
                fieldName: "1",
                resModel: "partner",
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_selector_chain_part").textContent.trim(),
            "1",
            "field name value should be 1."
        );
    });

    QUnit.test("create a field chain with value 0 i.e. FALSE_LEAF", async (assert) => {
        assert.expect(1);

        //create the field selector with domain value ["0"]
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                showSearchInput: false,
                fieldName: "0",
                resModel: "partner",
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_selector_chain_part").textContent.trim(),
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
            mockRPC(route, { method }) {
                if (method === "fields_get") {
                    assert.step("fields_get");
                }
            },
            props: {
                readonly: false,
                fieldName: "partner_id.partner_id.partner_id.foo",
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
                this.fieldName = "partner_id.foo";
            }
            onUpdate(value) {
                this.fieldName = value;
                this.render();
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                fieldName="fieldName"
                update="(value) => this.onUpdate(value)"
            />
        `;

        await mountComponent(Parent);

        assert.deepEqual(
            [...target.querySelectorAll(".o_field_selector_value span")].map((el) => el.innerText),
            ["Partner", "Foo"]
        );
        assert.containsNone(target, ".o_field_selector i.o_field_selector_warning");

        await click(target, ".o_field_selector");
        await click(target, ".o_field_selector_prev_page");

        assert.deepEqual(
            [...target.querySelectorAll(".o_field_selector_value span")].map((el) => el.innerText),
            ["Partner"]
        );
        assert.containsNone(target, ".o_field_selector i.o_field_selector_warning");

        await click(target, ".o_field_selector_prev_page");

        assert.deepEqual(
            [...target.querySelectorAll(".o_field_selector_value span")].map((el) => el.innerText),
            [""]
        );
        assert.containsOnce(target, ".o_field_selector i.o_field_selector_warning");

        await click(target, ".o_field_selector_popover .o_field_selector_item:nth-child(1)");

        assert.deepEqual(
            [...target.querySelectorAll(".o_field_selector_value span")].map((el) => el.innerText),
            ["Bar"]
        );

        assert.containsNone(target, ".o_field_selector_popover");
    });

    QUnit.test("can follow relations", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                fieldName: "",
                resModel: "partner",
                followRelations: true, // default
                update(value) {
                    assert.strictEqual(value, "product_id");
                },
            },
        });

        await click(target, ".o_field_selector");
        assert.containsOnce(
            target,
            ".o_field_selector_item:last-child .o_field_selector_relation_icon"
        );
        await click(target, ".o_field_selector_item:last-child .o_field_selector_relation_icon");
        assert.containsOnce(target, ".o_popover");
    });

    QUnit.test("cannot follow relations", async (assert) => {
        await mountComponent(ModelFieldSelector, {
            props: {
                readonly: false,
                fieldName: "",
                resModel: "partner",
                followRelations: false,
                update(value) {
                    assert.strictEqual(value, "product_id");
                },
            },
        });

        await click(target, ".o_field_selector");
        assert.containsNone(target, ".o_field_selector_relation_icon");
        await click(target, ".o_field_selector_item:last-child");
        assert.containsNone(target, ".o_popover");
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
                this.fieldName = "foo";
            }
            onUpdate(value) {
                this.fieldName = value;
                this.render();
            }
        }
        Parent.components = { ModelFieldSelector };
        Parent.template = xml`
                    <ModelFieldSelector
                        readonly="false"
                        resModel="'partner'"
                        fieldName="fieldName"
                        isDebugMode="true"
                        update="(value) => this.onUpdate(value)"
                    />
                `;

        await mountComponent(Parent);

        assert.deepEqual(
            [...target.querySelectorAll(".o_field_selector_value span")].map((el) => el.innerText),
            ["Foo"]
        );

        await click(target, ".o_field_selector");

        await editInput(
            target,
            ".o_field_selector_popover .o_field_selector_debug",
            "partner_id.bar"
        );

        assert.deepEqual(
            [...target.querySelectorAll(".o_field_selector_value span")].map((el) => el.innerText),
            ["Partner", "Bar"]
        );
    });
});
