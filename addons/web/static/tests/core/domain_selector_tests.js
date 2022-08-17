/** @odoo-module **/

import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { ormService } from "@web/core/orm_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { viewService } from "@web/views/view_service";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, mount, triggerEvent } from "../helpers/utils";
import { makeFakeLocalizationService } from "../helpers/mock_services";

const { Component, xml } = owl;

let serverData;
let target;

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
                        datetime: { string: "Date Time", type: "datetime", searchable: true },
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
        registry.category("services").add("ui", uiService);
        registry.category("services").add("hotkey", hotkeyService);
        registry.category("services").add("localization", makeFakeLocalizationService());
        registry.category("services").add("view", viewService);

        target = getFixture();
    });

    QUnit.module("DomainSelector");

    QUnit.test("creating a domain from scratch", async (assert) => {
        assert.expect(12);

        class Parent extends Component {
            setup() {
                this.value = "[]";
            }
            onUpdate(newValue) {
                this.value = newValue;
                this.render();
            }
        }
        Parent.components = { DomainSelector };
        Parent.template = xml`
            <DomainSelector
                resModel="'partner'"
                value="value"
                readonly="false"
                isDebugMode="true"
                update="(newValue) => this.onUpdate(newValue)"
            />
        `;

        // Create the domain selector and its mock environment
        await mountComponent(Parent, {
            props: {
                resModel: "partner",
                value: "[]",
                readonly: false,
                isDebugMode: true,
            },
        });

        // As we gave an empty domain, there should be a visible button to add
        // the first domain part
        assert.containsOnce(
            target,
            ".o_domain_add_first_node_button",
            "there should be a button to create first domain element"
        );

        // Clicking on the button should add a visible field selector in the
        // widget so that the user can change the field chain
        await click(target, ".o_domain_add_first_node_button");
        assert.containsOnce(target, ".o_field_selector", "there should be a field selector");

        // Focusing the field selector input should open a field selector popover
        await click(target, ".o_field_selector");
        assert.containsOnce(
            document.body,
            ".o_field_selector_popover",
            "field selector popover should be visible"
        );

        // The field selector popover should contain the list of "partner"
        // fields. "Bar" should be among them.
        assert.strictEqual(
            document.body.querySelector(".o_field_selector_popover li").textContent,
            "Bar",
            "field selector popover should contain the 'Bar' field"
        );

        // Clicking the "Bar" field should change the internal domain and this
        // should be displayed in the debug textarea
        await click(document.body.querySelector(".o_field_selector_popover li"));
        assert.containsOnce(target, "textarea.o_domain_debug_input");
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            `[("bar", "=", True)]`,
            "the domain input should contain a domain with 'bar'"
        );

        // There should be a "+" button to add a domain part; clicking on it
        // should add the default "['id', '=', 1]" domain
        assert.containsOnce(target, ".fa-plus-circle", "there should be a '+' button");
        await click(target, ".fa-plus-circle");
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            `["&", ("bar", "=", True), ("id", "=", 1)]`,
            "the domain input should contain a domain with 'bar' and 'id'"
        );

        // There should be two "..." buttons to add a domain group; clicking on
        // the first one, should add this group with defaults "['id', '=', 1]"
        // domains and the "|" operator
        assert.containsN(target, ".fa-ellipsis-h", 2, "there should be two '...' buttons");

        await click(target.querySelector(".fa-ellipsis-h"));
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            `["&", ("bar", "=", True), "&", "|", ("id", "=", 1), ("id", "=", 1), ("id", "=", 1)]`,
            "the domain input should contain a domain with 'bar', 'id' and a subgroup"
        );

        // There should be five "-" buttons to remove domain part; clicking on
        // the two last ones, should leave a domain with only the "bar" and
        // "foo" fields, with the initial "&" operator
        assert.containsN(
            target,
            ".o_domain_delete_node_button",
            5,
            "there should be five 'x' buttons"
        );
        let buttons = target.querySelectorAll(".o_domain_delete_node_button");
        await click(buttons[buttons.length - 1]);
        buttons = target.querySelectorAll(".o_domain_delete_node_button");
        await click(buttons[buttons.length - 1]);
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            `["&", ("bar", "=", True), ("id", "=", 1)]`,
            "the domain input should contain a domain with 'bar' and 'id'"
        );
    });

    QUnit.test("building a domain with a datetime", async (assert) => {
        assert.expect(2);

        // Create the domain selector and its mock environment
        await mountComponent(DomainSelector, {
            props: {
                resModel: "partner",
                value: `[("datetime", "=", "2017-03-27 15:42:00")]`,
                readonly: false,
                update: (newValue) => {
                    assert.strictEqual(
                        newValue,
                        `[("datetime", "=", "2017-02-26 15:42:00")]`,
                        "datepicker value should have changed"
                    );
                },
            },
        });

        // Check that there is a datepicker to choose the date
        assert.containsOnce(target, ".o_datepicker", "there should be a datepicker");
        await click(target, ".o_datepicker_input");

        await click(
            document.body.querySelector(
                `.bootstrap-datetimepicker-widget :not(.today)[data-action="selectDay"]`
            )
        ); // => February 26th
        await click(
            document.body.querySelector(`.bootstrap-datetimepicker-widget a[data-action="close"]`)
        );
    });

    QUnit.test("building a domain with a m2o without following the relation", async (assert) => {
        assert.expect(1);

        // Create the domain selector and its mock environment
        await mountComponent(DomainSelector, {
            props: {
                resModel: "partner",
                value: `[("product_id", "ilike", 1)]`,
                readonly: false,
                isDebugMode: true,
                update: (newValue) => {
                    assert.strictEqual(
                        newValue,
                        `[("product_id", "ilike", "pad")]`,
                        "string should have been allowed as m2o value"
                    );
                },
            },
        });

        const input = target.querySelector(".o_domain_leaf_value_input");
        input.value = "pad";
        await triggerEvent(input, null, "change");
    });

    QUnit.test("editing a domain with `parent` key", async (assert) => {
        assert.expect(1);

        // Create the domain selector and its mock environment
        await mountComponent(DomainSelector, {
            props: {
                resModel: "product",
                value: `[("name", "=", parent.foo)]`,
                readonly: false,
                isDebugMode: true,
            },
        });
        assert.strictEqual(
            target.lastElementChild.innerHTML,
            "This domain is not supported.",
            "an error message should be displayed because of the `parent` key"
        );
    });

    QUnit.test("creating a domain with a default option", async (assert) => {
        assert.expect(1);

        // Create the domain selector and its mock environment
        await mountComponent(DomainSelector, {
            props: {
                resModel: "partner",
                value: "[]",
                readonly: false,
                isDebugMode: true,
                defaultLeafValue: ["foo", "=", "kikou"],
                update: (newValue) => {
                    assert.strictEqual(
                        newValue,
                        `[("foo", "=", "kikou")]`,
                        "the domain input should contain the default domain"
                    );
                },
            },
        });

        // Clicking on the button should add a visible field selector in the
        // widget so that the user can change the field chain
        await click(target, ".o_domain_add_first_node_button");
    });

    QUnit.test("edit a domain with the debug textarea", async (assert) => {
        assert.expect(5);

        let newValue;

        class Parent extends Component {
            setup() {
                this.value = `[("product_id", "ilike", 1)]`;
            }
            onUpdate(value, fromDebug) {
                assert.strictEqual(value, newValue);
                assert.ok(fromDebug);
            }
        }
        Parent.components = { DomainSelector };
        Parent.template = xml`
            <DomainSelector
                value="value"
                resModel="'partner'"
                readonly="false"
                isDebugMode="true"
                update="(...args) => this.onUpdate(...args)"
            />
        `;
        // Create the domain selector and its mock environment
        await mountComponent(Parent);

        assert.containsOnce(
            target,
            ".o_domain_node.o_domain_leaf",
            "should have a single domain node"
        );
        newValue = `
[
    ['product_id', 'ilike', 1],
    ['id', '=', 0]
]`;
        const input = target.querySelector(".o_domain_debug_input");
        input.value = newValue;
        await triggerEvent(input, null, "change");
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            newValue,
            "the domain should not have been formatted"
        );
        assert.containsOnce(
            target,
            ".o_domain_node.o_domain_leaf",
            "should still have a single domain node"
        );
    });

    QUnit.test("operator fallback", async (assert) => {
        await mountComponent(DomainSelector, {
            props: {
                resModel: "partner",
                value: "[['foo', 'like', 'kikou']]",
            },
        });

        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Foo like "kikou"`);
    });

    QUnit.test("operator fallback in edit mode", async (assert) => {
        registry.category("domain_selector/operator").add("test", {
            category: "test",
            label: "test",
            value: "test",
            onDidChange: () => null,
            matches: ({ operator }) => operator === "test",
            hideValue: true,
        });

        await mountComponent(DomainSelector, {
            props: {
                readonly: false,
                resModel: "partner",
                value: "[['foo', 'test', 'kikou']]",
            },
        });

        // check that the DomainSelector does not crash
        assert.containsOnce(target, ".o_domain_selector");
        assert.containsN(target, ".o_domain_leaf_edition > div", 2, "value should be hidden");
    });

    QUnit.test("cache fields_get", async (assert) => {
        await mountComponent(DomainSelector, {
            mockRPC(route, { method }) {
                if (method === "fields_get") {
                    assert.step("fields_get");
                }
            },
            props: {
                readonly: false,
                resModel: "partner",
                value: "['&', ['foo', '=', 'kikou'], ['bar', '=', 'true']]",
            },
        });

        assert.verifySteps(["fields_get"]);
    });
});
