/** @odoo-module **/

import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, triggerEvent } from "../helpers/utils";
import { registerCleanup } from "../helpers/cleanup";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";

const { Component, mount } = owl;
const { xml } = owl.tags;

let env;
let target;
let fieldSelector;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        const serverData = {
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

        env = await makeTestEnv({ serverData });
        target = getFixture();

        const mainComponentsContainer = await mount(MainComponentsContainer, {
            env,
            target,
        });
        registerCleanup(() => mainComponentsContainer.destroy());
        registerCleanup(() => fieldSelector.destroy());
    });

    QUnit.module("ModelFieldSelector");

    QUnit.test("creating a field chain from scratch", async (assert) => {
        assert.expect(14);

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
                isDebugMode="true"
                update="(value) => this.onUpdate(value)"
            />
        `;

        // Create the field selector and its mock environment
        fieldSelector = await mount(Parent, {
            env,
            target,
            props: {},
        });

        // Focusing the field selector input should open a field selector popover
        await click(fieldSelector.el);
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
        await click(fieldSelector.el);
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
        await click(fieldSelector.el);
        await click(target, ".o_field_selector_prev_page");
        await click(target, ".o_field_selector_close");

        await click(fieldSelector.el);
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
        fieldSelector = await mount(ModelFieldSelector, {
            env,
            target,
            props: {
                readonly: false,
                fieldName: "product_id",
                resModel: "partner",
                isDebugMode: true,
            },
        });

        // Focusing the field selector input should open a field selector popover
        await click(fieldSelector.el);
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
        fieldSelector = await mount(ModelFieldSelector, {
            env,
            target,
            props: {
                readonly: false,
                fieldName: "",
                resModel: "partner",
                filter: (field) => field.type === "many2one",
            },
        });

        await click(fieldSelector.el);
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
        fieldSelector = await mount(ModelFieldSelector, {
            env,
            target,
            props: {
                readonly: false,
                fieldName: "",
                resModel: "partner",
            },
        });

        await click(fieldSelector.el);
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
        fieldSelector = await mount(ModelFieldSelector, {
            env,
            target,
            props: {
                readonly: false,
                showSearchInput: false,
                fieldName: "",
                resModel: "partner",
            },
        });

        await click(fieldSelector.el);
        assert.containsNone(
            target,
            ".o_field_selector_popover .o_field_selector_search",
            "there should be no search input"
        );
    });

    QUnit.test("create a field chain with value 1 i.e. TRUE_LEAF", async (assert) => {
        assert.expect(1);

        //create the field selector with domain value ["1"]
        fieldSelector = await mount(ModelFieldSelector, {
            env,
            target,
            props: {
                readonly: false,
                showSearchInput: false,
                fieldName: "1",
                resModel: "partner",
            },
        });

        assert.strictEqual(
            fieldSelector.el.querySelector(".o_field_selector_chain_part").textContent.trim(),
            "1",
            "field name value should be 1."
        );

        fieldSelector.destroy();
    });

    QUnit.test("create a field chain with value 0 i.e. FALSE_LEAF", async (assert) => {
        assert.expect(1);

        //create the field selector with domain value ["0"]
        fieldSelector = await mount(ModelFieldSelector, {
            env,
            target,
            props: {
                readonly: false,
                showSearchInput: false,
                fieldName: "0",
                resModel: "partner",
            },
        });

        assert.strictEqual(
            fieldSelector.el.querySelector(".o_field_selector_chain_part").textContent.trim(),
            "0",
            "field name value should be 0."
        );

        fieldSelector.destroy();
    });
});
