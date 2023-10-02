/** @odoo-module **/

import {
    click,
    editInput,
    editSelect,
    getFixture,
    getNodesTextContent,
    mount,
    nextTick,
    patchDate,
    patchTimeZone,
    patchWithCleanup,
    triggerEvent,
} from "../helpers/utils";
import { Component, useState, xml } from "@odoo/owl";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { fieldService } from "@web/core/field_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { makeTestEnv } from "../helpers/mock_env";
import { ormService } from "@web/core/orm_service";
import { OPERATOR_DESCRIPTIONS } from "@web/core/domain_selector/domain_selector_operators";
import { popoverService } from "@web/core/popover/popover_service";
import { registerCleanup } from "../helpers/cleanup";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { getPickerApplyButton, getPickerCell } from "./datetime/datetime_test_helpers";
import { openModelFieldSelectorPopover } from "./model_field_selector_tests";
import { nameService } from "@web/core/name_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { browser } from "@web/core/browser/browser";
import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";

let serverData;
let target;

function addProductIds() {
    serverData.models.partner.fields.product_ids = {
        string: "Products",
        type: "many2many",
        relation: "product",
        searchable: true,
    };
}

async function selectOperator(el, operator, index = 0) {
    const select = el.querySelectorAll("select.o_domain_leaf_operator_select")[index];
    await editSelect(select, null, operator);
}

function getOperatorOptions(el, index = 0) {
    const select = el.querySelectorAll("select.o_domain_leaf_operator_select")[index];
    return [...select.options].map((o) => o.label);
}

function getSelectedOperator(el, index = 0) {
    const select = el.querySelectorAll("select.o_domain_leaf_operator_select")[index];
    return select.options[select.selectedIndex].label;
}

function getAutocompletValue(target, index = 0) {
    return target.querySelectorAll(".o_ds_value_cell .o-autocomplete--input")[index].value;
}

async function mountComponent(Component, params = {}) {
    const env = await makeTestEnv({ serverData, mockRPC: params.mockRPC });
    await mount(MainComponentsContainer, target, { env });
    return mount(Component, target, { env, props: params.props || {} });
}

async function makeDomainSelector(params = {}) {
    const props = { ...params };
    const mockRPC = props.mockRPC;
    delete props.mockRPC;

    class Parent extends Component {
        setup() {
            this.domainSelectorProps = {
                resModel: "partner",
                readonly: false,
                domain: "[]",
                ...props,
                update: (domain, fromDebug) => {
                    if (props.update) {
                        props.update(domain, fromDebug);
                    }
                    this.domainSelectorProps.domain = domain;
                    this.render();
                },
            };
        }
        async set(domain) {
            this.domainSelectorProps.domain = domain;
            this.render();
            await nextTick();
        }
    }
    Parent.components = { DomainSelector };
    Parent.template = xml`<DomainSelector t-props="domainSelectorProps"/>`;

    const env = await makeTestEnv({ serverData, mockRPC });
    await mount(MainComponentsContainer, target, { env });
    return mount(Parent, target, { env, props });
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
                        date: { string: "Date", type: "date", searchable: true },
                        datetime: { string: "Date Time", type: "datetime", searchable: true },
                        int: { string: "Integer", type: "integer", searchable: true },
                        json_field: { string: "Json Field", type: "json", searchable: true },
                        state: {
                            string: "State",
                            type: "selection",
                            selection: [
                                ["abc", "ABC"],
                                ["def", "DEF"],
                                ["ghi", "GHI"],
                            ],
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
        registry.category("services").add("ui", uiService);
        registry.category("services").add("hotkey", hotkeyService);
        registry.category("services").add("localization", makeFakeLocalizationService());
        registry.category("services").add("field", fieldService);
        registry.category("services").add("name", nameService);
        registry.category("services").add("dialog", dialogService);
        registry.category("services").add("datetime_picker", datetimePickerService);

        target = getFixture();
    });

    QUnit.module("DomainSelector");

    QUnit.test("creating a domain from scratch", async (assert) => {
        await makeDomainSelector({
            isDebugMode: true,
        });

        // When we have an empty domain, the "New Rule" button should be available
        assert.containsOnce(
            target,
            "a[role=button]",
            "there should be a button to create a domain element"
        );

        // Clicking on the button should add a visible field selector in the
        // widget so that the user can change the field chain
        await click(target, "a[role=button]");
        assert.containsOnce(target, ".o_model_field_selector");

        // Focusing the field selector input should open a field selector popover
        await click(target, ".o_model_field_selector");
        assert.containsOnce(
            document.body,
            ".o_model_field_selector_popover",
            "field selector popover should be visible"
        );

        // The field selector popover should contain the list of "partner"
        // fields. "Bar" should be among them. "Bar" result li will display the
        // name of the field and some debug info.
        assert.strictEqual(
            document.body.querySelector(
                ".o_model_field_selector_popover .o_model_field_selector_popover_item_name"
            ).textContent,
            "Barbar (boolean)",
            "field selector popover should contain the 'Bar' field"
        );

        // Clicking the "Bar" field should change the internal domain and this
        // should be displayed in the debug textarea
        await click(
            document.body.querySelector(
                ".o_model_field_selector_popover .o_model_field_selector_popover_item_name"
            )
        );
        assert.containsOnce(target, "textarea.o_domain_debug_input");
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            `[("bar", "=", True)]`,
            "the domain input should contain a domain with 'bar'"
        );

        // There should be a "+" button to add a domain part; clicking on it
        // should add the default "['id', '=', 1]" domain
        assert.containsOnce(target, ".fa.fa-plus", "there should be a '+' button");
        await click(target, ".fa.fa-plus");
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            `["&", ("bar", "=", True), ("bar", "=", True)]`,
            "the domain input should contain a domain with 'bar' and 'id'"
        );

        // There should be two "add group" buttons to add a domain group; clicking on
        // the first one, should add this group with defaults "['id', '=', 1]"
        // domains and the "|" operator
        assert.containsN(target, ".fa.fa-sitemap", 2, "there should be two '...' buttons");

        await click(target.querySelector(".fa.fa-sitemap"));
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            `["&", "&", ("bar", "=", True), "|", ("id", "=", 1), ("id", "=", 1), ("bar", "=", True)]`,
            "the domain input should contain a domain with 'bar', 'id' and a subgroup"
        );

        // There should be five buttons to remove domain part; clicking on
        // the two last ones, should leave a domain with only the "bar" and
        // "foo" fields, with the initial "&" operator
        assert.containsN(
            target,
            ".o_domain_delete_node_button",
            5,
            "there should be five 'x' buttons"
        );
        let buttons = target.querySelectorAll(".o_domain_delete_node_button .fa.fa-trash");
        await click(buttons[buttons.length - 1]);
        buttons = target.querySelectorAll(".o_domain_delete_node_button .fa.fa-trash");
        await click(buttons[buttons.length - 1]);
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            `["&", ("bar", "=", True), ("id", "=", 1)]`,
            "the domain input should contain a domain with 'bar' and 'id'"
        );
    });

    QUnit.test("building a domain with a datetime", async (assert) => {
        assert.expect(4);
        await makeDomainSelector({
            domain: `[("datetime", "=", "2017-03-27 15:42:00")]`,
            isDebugMode: true,
            update(domain) {
                assert.strictEqual(
                    domain,
                    `[("datetime", "=", "2017-02-26 15:42:00")]`,
                    "datepicker value should have changed"
                );
            },
        });

        // Check that there is a datepicker to choose the date
        assert.containsOnce(target, ".o_datetime_input", "there should be a datepicker");
        // The input field should display the date and time in the user's timezone
        assert.equal(target.querySelector(".o_datetime_input").value, "03/27/2017 16:42:00");

        // Change the date in the datepicker
        await click(target, ".o_datetime_input");
        await click(getPickerCell("26").at(0)); // => February 26th
        await click(getPickerApplyButton());

        // The input field should display the date and time in the user's timezone
        assert.equal(target.querySelector(".o_datetime_input").value, "02/26/2017 16:42:00");
    });

    QUnit.test("building a domain with an invalid path", async (assert) => {
        await makeDomainSelector({
            domain: `[("fooooooo", "=", "abc")]`,
            update(domain) {
                assert.strictEqual(domain, `[("bar", "=", True)]`);
            },
        });

        assert.strictEqual(target.querySelector(".o_model_field_selector").innerText, "fooooooo");
        assert.containsOnce(target, ".o_model_field_selector_warning");
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_warning").title,
            "Invalid field chain"
        );
        assert.containsN(target, ".o_domain_leaf_operator_select option", 18);
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "=");
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "abc");

        await click(target, ".o_model_field_selector");
        await click(target.querySelector(".o_model_field_selector_popover_item_name"));

        assert.strictEqual(target.querySelector(".o_model_field_selector").innerText, "Bar");
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "is");
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "true");
    });

    QUnit.test("building a domain with an invalid operator", async (assert) => {
        await makeDomainSelector({
            domain: `[("foo", "!!!!=!!!!", "abc")]`,
            update(domain) {
                assert.strictEqual(domain, `[("foo", "=", "")]`);
            },
        });

        assert.strictEqual(target.querySelector(".o_model_field_selector").innerText, "Foo");
        assert.containsNone(target, ".o_model_field_selector_warning");
        assert.containsN(target, ".o_domain_leaf_operator_select option", 8 + 1);
        assert.strictEqual(getSelectedOperator(target), `"!!!!=!!!!"`);
        assert.containsNone(
            target,
            ".o_domain_leaf_value_input",
            "do not show editor if operator is invalid"
        );

        await editSelect(target, ".o_domain_leaf_operator_select", "=");

        assert.strictEqual(target.querySelector(".o_model_field_selector").innerText, "Foo");
        assert.containsNone(target, ".o_model_field_selector_warning");
        assert.containsN(target, ".o_domain_leaf_operator_select option", 8);
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "=");
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "");
    });

    QUnit.test("building a domain with an expression for value", async (assert) => {
        patchDate(2023, 3, 20, 17, 0, 0);
        await makeDomainSelector({
            domain: `[("datetime", ">=", context_today())]`,
            update(domain) {
                assert.strictEqual(domain, `[("datetime", ">=", "2023-04-20 16:00:00")]`);
            },
        });

        assert.containsNone(target, ".o_ds_value_cell input");
        assert.containsOnce(target, ".o_ds_expr_value");
        assert.strictEqual(target.querySelector(".o_ds_expr_value").textContent, "context_today()");

        await click(target, ".o_ds_expr_value button");
        assert.containsOnce(target, ".o_ds_value_cell input");
        assert.containsNone(target, ".o_ds_expr_value");
        assert.strictEqual(
            target.querySelector(".o_ds_value_cell input").value,
            "04/20/2023 17:00:00"
        );
    });

    QUnit.test("building a domain with an expression in value", async (assert) => {
        await makeDomainSelector({
            domain: `[("int", "=", id)]`,
            update(domain) {
                assert.strictEqual(domain, `[("int", "<", 1)]`);
            },
        });

        assert.strictEqual(target.querySelector(".o_model_field_selector").innerText, "Integer");
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "=");
        assert.containsNone(target, ".o_ds_value_cell input");
        assert.containsOnce(target, ".o_ds_expr_value");
        assert.strictEqual(target.querySelector(".o_ds_expr_value").textContent, "id");

        await editSelect(target, ".o_domain_leaf_operator_select", "<");
        assert.strictEqual(target.querySelector(".o_model_field_selector").innerText, "Integer");
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "<");
        assert.containsOnce(target, ".o_ds_value_cell input");
        assert.containsNone(target, ".o_ds_expr_value");
        assert.strictEqual(target.querySelector(".o_ds_value_cell input").value, "1");
    });

    QUnit.test("building a domain with a m2o without following the relation", async (assert) => {
        await makeDomainSelector({
            domain: `[("product_id", "ilike", 1)]`,
            isDebugMode: true,
            update: (domain) => {
                assert.step(domain);
            },
        });
        assert.verifySteps([]);
        assert.containsOnce(target, ".o_ds_expr_value");

        await click(target, ".o_ds_expr_value button");
        assert.verifySteps([`[("product_id", "ilike", "")]`]);

        const input = target.querySelector(".o_domain_leaf_value_input");
        input.value = "pad";
        await triggerEvent(input, null, "change");
        assert.verifySteps([`[("product_id", "ilike", "pad")]`]);
    });

    QUnit.test("editing a domain with `parent` key", async (assert) => {
        await makeDomainSelector({
            resModel: "product",
            domain: `[("name", "=", parent.foo)]`,
            isDebugMode: true,
        });
        assert.containsOnce(target, ".o_ds_expr_value");
        assert.strictEqual(target.querySelector(".o_ds_expr_value").textContent, "parent.foo");
    });

    QUnit.test("creating a domain with a default option", async (assert) => {
        assert.expect(1);
        // Create the domain selector and its mock environment
        await makeDomainSelector({
            isDebugMode: true,
            defaultLeafValue: ["foo", "=", "kikou"],
            update: (domain) => {
                assert.strictEqual(
                    domain,
                    `[("foo", "=", "kikou")]`,
                    "the domain input should contain the default domain"
                );
            },
        });
        // Clicking on the button should add a visible field selector in the
        // widget so that the user can change the field chain
        await click(target, "a[role=button]");
    });

    QUnit.test("edit a domain with the debug textarea", async (assert) => {
        assert.expect(5);

        let newDomain;
        await makeDomainSelector({
            domain: `[("product_id", "ilike", 1)]`,
            isDebugMode: true,
            update(domain, fromDebug) {
                assert.strictEqual(domain, newDomain);
                assert.ok(fromDebug);
            },
        });
        assert.containsOnce(
            target,
            ".o_domain_node.o_domain_leaf",
            "should have a single domain node"
        );

        newDomain = `
            [
                ['product_id', 'ilike', 1],
                ['id', '=', 0]
            ]
        `;
        await editInput(target, ".o_domain_debug_input", newDomain);
        assert.strictEqual(
            target.querySelector(".o_domain_debug_input").value,
            newDomain,
            "the domain should not have been formatted"
        );
        assert.containsN(target, ".o_domain_node.o_domain_leaf", 2);
    });

    QUnit.test(
        "set [(1, '=', 1)] or [(0, '=', 1)] as domain with the debug textarea",
        async (assert) => {
            assert.expect(15);

            let newDomain;
            await makeDomainSelector({
                domain: `[("product_id", "ilike", 1)]`,
                isDebugMode: true,
                update(domain, fromDebug) {
                    assert.strictEqual(domain, newDomain);
                    assert.ok(fromDebug);
                },
            });
            assert.containsOnce(
                target,
                ".o_domain_node.o_domain_leaf",
                "should have a single domain node"
            );
            newDomain = `[(1, "=", 1)]`;
            let input = target.querySelector(".o_domain_debug_input");
            input.value = newDomain;
            await triggerEvent(input, null, "change");
            assert.strictEqual(
                target.querySelector(".o_domain_debug_input").value,
                newDomain,
                "the domain should not have been formatted"
            );
            assert.containsOnce(
                target,
                ".o_domain_node.o_domain_leaf",
                "should still have a single domain node"
            );

            assert.strictEqual(
                target.querySelector(".o_model_field_selector_chain_part").innerText,
                "1"
            );
            assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "=");
            assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "1");

            newDomain = `[(0, "=", 1)]`;
            input = target.querySelector(".o_domain_debug_input");
            input.value = newDomain;
            await triggerEvent(input, null, "change");
            assert.strictEqual(
                target.querySelector(".o_domain_debug_input").value,
                newDomain,
                "the domain should not have been formatted"
            );
            assert.containsOnce(
                target,
                ".o_domain_node.o_domain_leaf",
                "should still have a single domain node"
            );

            assert.strictEqual(
                target.querySelector(".o_model_field_selector_chain_part").innerText,
                "0"
            );
            assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "=");
            assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "1");
        }
    );

    QUnit.test("operator fallback (readonly mode)", async (assert) => {
        await makeDomainSelector({
            domain: `[['foo', 'like', 'kikou']]`,
            readonly: true,
        });
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Foo like kikou`);
    });

    QUnit.test("operator fallback (edit mode)", async (assert) => {
        OPERATOR_DESCRIPTIONS.test = {
            label: "test",
            valueCount: 0,
        };
        registerCleanup(() => {
            delete OPERATOR_DESCRIPTIONS.test;
        });

        await makeDomainSelector({ domain: "[['foo', 'test', 'kikou']]" });
        // check that the DomainSelector does not crash
        assert.containsOnce(target, ".o_domain_selector");
        assert.containsN(target, ".o_domain_leaf_edition > div", 2, "value should be hidden");
    });

    QUnit.test("cache fields_get", async (assert) => {
        await makeDomainSelector({
            domain: "['&', ['foo', '=', 'kikou'], ['bar', '=', 'true']]",
            mockRPC(_, { method }) {
                if (method === "fields_get") {
                    assert.step("fields_get");
                }
            },
        });

        assert.verifySteps(["fields_get"]);
    });

    QUnit.test("selection field with operator change from 'is set' to '='", async (assert) => {
        await makeDomainSelector({ domain: `[['state', '!=', False]]` });

        assert.strictEqual(
            target.querySelector(".o_model_field_selector_chain_part").innerText,
            "State"
        );
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "set");

        await editSelect(target, ".o_domain_leaf_operator_select", "=");

        assert.strictEqual(
            target.querySelector(".o_model_field_selector_chain_part").innerText,
            "State"
        );
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "=");
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, `"abc"`);
    });

    QUnit.test("show correct operator", async (assert) => {
        await makeDomainSelector({ domain: `[['state', 'in', ['abc']]]` });
        const select = target.querySelector(".o_domain_leaf_operator_select");
        assert.strictEqual(select.options[select.options.selectedIndex].text, "is in");
    });

    QUnit.test("multi selection", async (assert) => {
        class Parent extends Component {
            setup() {
                this.domain = `[("state", "in", ["a", "b", "c"])]`;
            }
            onUpdate(domain) {
                this.domain = domain;
                this.render();
            }
        }
        Parent.components = { DomainSelector };
        Parent.template = xml`
            <DomainSelector
                resModel="'partner'"
                domain="domain"
                readonly="false"
                update="(domain) => this.onUpdate(domain)"
            />
        `;

        // Create the domain selector and its mock environment
        const comp = await mountComponent(Parent);

        assert.containsOnce(target, ".o_domain_leaf_value_input");
        assert.strictEqual(comp.domain, `[("state", "in", ["a", "b", "c"])]`);
        assert.strictEqual(
            target.querySelector(".o_domain_leaf_value_input").value,
            `["a", "b", "c"]`
        );

        await editInput(target, ".o_domain_leaf_value_input", `[]`);
        assert.strictEqual(comp.domain, `[("state", "in", [])]`);

        await editInput(target, ".o_domain_leaf_value_input", `["b"]`);
        assert.strictEqual(comp.domain, `[("state", "in", ["b"])]`);
    });

    QUnit.test("json field with operator change from 'equal' to 'ilike'", async (assert) => {
        await makeDomainSelector({ domain: `[['json_field', '=', "hey"]]` });
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_chain_part").innerText,
            `Json Field`
        );
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "=");
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, `hey`);

        await editSelect(target, ".o_domain_leaf_operator_select", "ilike");
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "ilike");
    });

    QUnit.test("parse -1", async (assert) => {
        class Parent extends Component {
            setup() {
                this.domain = `[("id", "=", -1)]`;
            }
        }
        Parent.components = { DomainSelector };
        Parent.template = xml`
            <DomainSelector resModel="'partner'" domain="domain" readonly="false"/>
        `;
        await mountComponent(Parent);
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "-1");
    });

    QUnit.test("parse 3-1", async (assert) => {
        class Parent extends Component {
            setup() {
                this.domain = `[("id", "=", 3-1)]`;
            }
        }
        Parent.components = { DomainSelector };
        Parent.template = xml`
            <DomainSelector resModel="'partner'" domain="domain" readonly="false"/>
        `;
        await mountComponent(Parent);
        assert.strictEqual(target.querySelector(".o_ds_expr_value").innerText, "3 - 1");
    });

    QUnit.test("domain not supported (mode readonly)", async (assert) => {
        await mountComponent(DomainSelector, {
            props: {
                resModel: "partner",
                domain: `[`,
                readonly: true,
                isDebugMode: false,
            },
        });
        assert.containsNone(target, ".o_reset_domain_button");
        assert.containsNone(target, ".o_domain_debug_input");
    });

    QUnit.test("domain not supported (mode readonly + mode debug)", async (assert) => {
        await mountComponent(DomainSelector, {
            props: {
                resModel: "partner",
                domain: `[`,
                readonly: true,
                isDebugMode: true,
            },
        });
        assert.containsNone(target, ".o_reset_domain_button");
        assert.containsOnce(target, ".o_domain_debug_input");
        assert.ok(target.querySelector(".o_domain_debug_input").hasAttribute("readonly"));
    });

    QUnit.test("domain not supported (mode edit)", async (assert) => {
        await mountComponent(DomainSelector, {
            props: {
                resModel: "partner",
                domain: `[`,
                readonly: false,
                isDebugMode: false,
            },
        });
        assert.containsOnce(target, ".o_reset_domain_button");
        assert.containsNone(target, ".o_domain_debug_input");
    });

    QUnit.test("domain not supported (mode edit + mode debug)", async (assert) => {
        await mountComponent(DomainSelector, {
            props: {
                resModel: "partner",
                domain: `[`,
                readonly: false,
                isDebugMode: true,
            },
        });
        assert.containsOnce(target, ".o_reset_domain_button");
        assert.containsOnce(target, ".o_domain_debug_input");
        assert.notOk(target.querySelector(".o_domain_debug_input").hasAttribute("readonly"));
    });

    QUnit.test("reset domain", async (assert) => {
        class Parent extends Component {
            setup() {
                this.domain = `[`;
            }
            onUpdate(domain) {
                assert.step(domain);
                this.domain = domain;
                this.render();
            }
        }
        Parent.components = { DomainSelector };
        Parent.template = xml`
            <DomainSelector
                resModel="'partner'"
                domain="domain"
                readonly="false"
                update="(domain) => this.onUpdate(domain)"
            />
        `;
        await mountComponent(Parent);
        assert.strictEqual(
            target.querySelector(".o_domain_selector").innerText.toLowerCase(),
            "this domain is not supported. reset domain"
        );
        assert.containsOnce(target, ".o_reset_domain_button");
        assert.containsNone(target, ".o_domain_add_first_node_button");

        await click(target, ".o_reset_domain_button");
        assert.strictEqual(
            target.querySelector(".o_domain_selector").innerText.toLowerCase(),
            "match all records\nnew rule"
        );
        assert.containsNone(target, ".o_reset_domain_button");
        assert.containsOnce(target, "a[role=button]");
        assert.verifySteps(["[]"]);
    });

    QUnit.test("debug input in model field selector popover", async (assert) => {
        class Parent extends Component {
            setup() {
                this.domain = `[("id", "=", 1)]`;
            }
            onUpdate(domain) {
                assert.step(domain);
                this.domain = domain;
                this.render();
            }
        }
        Parent.components = { DomainSelector };
        Parent.template = xml`
            <DomainSelector
                resModel="'partner'"
                domain="domain"
                readonly="false"
                isDebugMode="true"
                update="(domain) => this.onUpdate(domain)"
            />
        `;
        await mountComponent(Parent);
        await openModelFieldSelectorPopover(target);
        await editInput(target, ".o_model_field_selector_debug", "a");
        await click(target, ".o_model_field_selector_popover_close");
        assert.verifySteps([`[("a", "=", "")]`]);

        assert.strictEqual(target.querySelector(".o_model_field_selector").innerText, "a");
        assert.containsOnce(target, ".o_model_field_selector_warning");
        assert.containsN(target, ".o_domain_leaf_operator_select option", 18);
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "=");
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "");
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, `[("a", "=", "")]`);
    });

    QUnit.test("between operator", async (assert) => {
        patchTimeZone(0);
        await makeDomainSelector({
            domain: `["&", ("datetime", ">=", "2023-01-01 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00")]`,
            isDebugMode: true,
            update(domain) {
                assert.step(domain);
            },
        });

        assert.containsOnce(target, ".o_domain_leaf");
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "between");
        assert.containsN(target, ".o_datetime_input", 2);

        await editInput(
            target.querySelectorAll(".o_datetime_input")[0],
            null,
            "2023-01-02 00:00:00"
        );
        assert.verifySteps([
            `["&", ("datetime", ">=", "2023-01-02 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00")]`,
        ]);

        await editInput(
            target.querySelectorAll(".o_datetime_input")[1],
            null,
            "2023-01-08 00:00:00"
        );
        assert.verifySteps([
            `["&", ("datetime", ">=", "2023-01-02 00:00:00"), ("datetime", "<=", "2023-01-08 00:00:00")]`,
        ]);
    });

    QUnit.test("between operator (2)", async (assert) => {
        patchTimeZone(0);
        await makeDomainSelector({
            domain: `["&", "&", ("foo", "=", "abc"), ("datetime", ">=", "2023-01-01 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00")]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.containsN(target, ".o_domain_leaf", 2);
        assert.strictEqual(
            target.querySelector(".o_domain_leaf .o_domain_leaf_operator_select ").value,
            "="
        );
        assert.strictEqual(
            target.querySelector(".o_domain_leaf:nth-child(2) .o_domain_leaf_operator_select ")
                .value,
            "between"
        );
        assert.containsN(target, ".o_datetime_input", 2);
    });

    QUnit.test("between operator (3)", async (assert) => {
        patchTimeZone(0);
        await makeDomainSelector({
            domain: `["&", "&", ("datetime", ">=", "2023-01-01 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00"), ("foo", "=", "abc")]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.containsN(target, ".o_domain_leaf", 2);
        assert.strictEqual(
            target.querySelector(".o_domain_leaf .o_domain_leaf_operator_select ").value,
            "between"
        );
        assert.strictEqual(
            target.querySelector(".o_domain_leaf:nth-child(2) .o_domain_leaf_operator_select ")
                .value,
            "="
        );
        assert.containsN(target, ".o_datetime_input", 2);
    });

    QUnit.test("between operator (4)", async (assert) => {
        patchTimeZone(0);
        await makeDomainSelector({
            domain: `["&", ("datetime", ">=", "2023-01-01 00:00:00"), "&", ("datetime", "<=", "2023-01-10 00:00:00"), ("foo", "=", "abc")]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.containsN(target, ".o_domain_leaf", 2);
        assert.strictEqual(
            target.querySelector(".o_domain_leaf .o_domain_leaf_operator_select ").value,
            "between"
        );
        assert.strictEqual(
            target.querySelector(".o_domain_leaf:nth-child(2) .o_domain_leaf_operator_select ")
                .value,
            "="
        );
        assert.containsN(target, ".o_datetime_input", 2);
    });

    QUnit.test("between operator (5)", async (assert) => {
        patchTimeZone(0);
        await makeDomainSelector({
            domain: `["|", "&", ("create_date", ">=", "2023-04-01 00:00:00"), ("create_date", "<=", "2023-04-30 23:59:59"), (0, "=", 1)]`,
            readonly: true,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(
            target.querySelector(".o_domain_selector").innerText,
            `Match any of the following rules:\ncreate_date\nis between 2023-04-01 00:00:00 and 2023-04-30 23:59:59\n0\n= 1`
        );
    });

    QUnit.test("expressions in between operator", async (assert) => {
        patchTimeZone(0);
        patchDate(2023, 0, 1, 0, 0, 0);
        await makeDomainSelector({
            domain: `["&", ("datetime", ">=", context_today()), ("datetime", "<=", "2023-01-10 00:00:00")]`,
            update(domain) {
                assert.step(domain);
            },
        });

        assert.containsOnce(target, ".o_domain_leaf");
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "between");
        assert.containsOnce(target, ".o_ds_expr_value");
        assert.containsOnce(target, ".o_datetime_input");

        await click(target, ".o_ds_expr_value button");
        assert.verifySteps([
            `["&", ("datetime", ">=", "2023-01-01 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00")]`,
        ]);
    });

    QUnit.test("support of connector '!' (readonly mode)", async (assert) => {
        const toTest = [
            {
                domain: `["!", ("foo", "=", "abc")]`,
                result: `Match all of the following rules:\nFoo\n!= abc`,
            },
            {
                domain: `["!", "!", ("foo", "=", "abc")]`,
                result: `Match all of the following rules:\nFoo\n= abc`,
            },
            {
                domain: `["!", "!", "!", ("foo", "=", "abc")]`,
                result: `Match all of the following rules:\nFoo\n!= abc`,
            },
            {
                domain: `["!", "&", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match any of the following rules:\nFoo\n!= abc\nFoo\n!= def`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match all of the following rules:\nFoo\n!= abc\nFoo\n!= def`,
            },
            {
                domain: `["&", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match all of the following rules:\nFoo\n!= abc\nFoo\n= def`,
            },
            {
                domain: `["&", "!", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match all of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["&", ("foo", "=", "abc"), "!", ("foo", "=", "def")]`,
                result: `Match all of the following rules:\nFoo\n= abc\nFoo\n!= def`,
            },
            {
                domain: `["&", ("foo", "=", "abc"), "!", "!", ("foo", "=", "def")]`,
                result: `Match all of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["|", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match any of the following rules:\nFoo\n!= abc\nFoo\n= def`,
            },
            {
                domain: `["|", "!", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match any of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["|", ("foo", "=", "abc"), "!", ("foo", "=", "def")]`,
                result: `Match any of the following rules:\nFoo\n= abc\nFoo\n!= def`,
            },
            {
                domain: `["|", ("foo", "=", "abc"), "!", "!", ("foo", "=", "def")]`,
                result: `Match any of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["&", "!", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match all of the following rules:\nany\nof:\nFoo\n!= abc\nFoo\n!= def\nFoo\n= ghi`,
            },
            {
                domain: `["&", "!", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match all of the following rules:\nFoo\n!= abc\nFoo\n!= def\nFoo\n= ghi`,
            },
            {
                domain: `["|", "!", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match any of the following rules:\nFoo\n!= abc\nFoo\n!= def\nFoo\n= ghi`,
            },
            {
                domain: `["|", "!", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match any of the following rules:\nall\nof:\nFoo\n!= abc\nFoo\n!= def\nFoo\n= ghi`,
            },
            {
                domain: `["!", "&", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match any of the following rules:\nFoo\n!= abc\nFoo\n!= def\nFoo\n!= ghi`,
            },
            {
                domain: `["!", "|", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match all of the following rules:\nFoo\n!= abc\nFoo\n!= def\nFoo\n!= ghi`,
            },
            {
                domain: `["!", "&", "|", ("foo", "=", "abc"), "!", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match any of the following rules:\nall\nof:\nFoo\n!= abc\nFoo\n= def\nFoo\n!= ghi`,
            },
            {
                domain: `["!", "|", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match all of the following rules:\nany\nof:\nFoo\n!= abc\nFoo\n!= def\nFoo\n!= ghi`,
            },
            {
                domain: `["!", "&", ("foo", "=", "abc"), "|", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match any of the following rules:\nFoo\n!= abc\nall\nof:\nFoo\n!= def\nFoo\n!= ghi`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), "&", ("foo", "=", "def"), ("foo", "!=", "ghi")]`,
                result: `Match all of the following rules:\nFoo\n!= abc\nany\nof:\nFoo\n!= def\nFoo\n= ghi`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), "&", ("foo", "!=", "def"), "!", ("foo", "=", "ghi")]`,
                result: `Match all of the following rules:\nFoo\n!= abc\nany\nof:\nFoo\n= def\nFoo\n= ghi`,
            },
        ];

        class Parent extends Component {
            setup() {
                this.state = useState({ domain: `[]` });
            }
        }
        Parent.components = { DomainSelector };
        Parent.template = xml`<DomainSelector resModel="'partner'" domain="state.domain"/>`;

        const parent = await mountComponent(Parent);

        for (const { domain, result } of toTest) {
            parent.state.domain = domain;
            await nextTick();
            assert.strictEqual(target.querySelector(".o_domain_selector").innerText, result);
        }
    });

    QUnit.test("support of connector '!' (debug mode)", async (assert) => {
        const toTest = [
            {
                domain: `["!", ("foo", "=", "abc")]`,
                result: `Match all of the following rules:\nFoo\n!= abc`,
            },
            {
                domain: `["!", "!", ("foo", "=", "abc")]`,
                result: `Match all of the following rules:\nFoo\n= abc`,
            },
            {
                domain: `["!", "!", "!", ("foo", "=", "abc")]`,
                result: `Match all of the following rules:\nFoo\n!= abc`,
            },
            {
                domain: `["!", "&", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match not all of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match none of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["&", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match all of the following rules:\nFoo\n!= abc\nFoo\n= def`,
            },
            {
                domain: `["&", "!", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match all of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["&", ("foo", "=", "abc"), "!", ("foo", "=", "def")]`,
                result: `Match all of the following rules:\nFoo\n= abc\nFoo\n!= def`,
            },
            {
                domain: `["&", ("foo", "=", "abc"), "!", "!", ("foo", "=", "def")]`,
                result: `Match all of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["|", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match any of the following rules:\nFoo\n!= abc\nFoo\n= def`,
            },
            {
                domain: `["|", "!", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match any of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["|", ("foo", "=", "abc"), "!", ("foo", "=", "def")]`,
                result: `Match any of the following rules:\nFoo\n= abc\nFoo\n!= def`,
            },
            {
                domain: `["|", ("foo", "=", "abc"), "!", "!", ("foo", "=", "def")]`,
                result: `Match any of the following rules:\nFoo\n= abc\nFoo\n= def`,
            },
            {
                domain: `["&", "!", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match all of the following rules:\nnot all\nof:\nFoo\n= abc\nFoo\n= def\nFoo\n= ghi`,
            },
            {
                domain: `["&", "!", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match all of the following rules:\nnone\nof:\nFoo\n= abc\nFoo\n= def\nFoo\n= ghi`,
            },
            {
                domain: `["|", "!", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match any of the following rules:\nnot all\nof:\nFoo\n= abc\nFoo\n= def\nFoo\n= ghi`,
            },
            {
                domain: `["|", "!", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match any of the following rules:\nnone\nof:\nFoo\n= abc\nFoo\n= def\nFoo\n= ghi`,
            },
            {
                domain: `["!", "&", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match not all of the following rules:\nFoo\n= abc\nFoo\n= def\nFoo\n= ghi`,
            },
            {
                domain: `["!", "|", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match none of the following rules:\nFoo\n= abc\nFoo\n= def\nFoo\n= ghi`,
            },
            {
                domain: `["!", "&", "|", ("foo", "=", "abc"), "!", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match not all of the following rules:\nany\nof:\nFoo\n= abc\nFoo\n!= def\nFoo\n= ghi`,
            },
            {
                domain: `["!", "|", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match none of the following rules:\nall\nof:\nFoo\n= abc\nFoo\n= def\nFoo\n= ghi`,
            },
            {
                domain: `["!", "&", ("foo", "=", "abc"), "|", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match not all of the following rules:\nFoo\n= abc\nany\nof:\nFoo\n= def\nFoo\n= ghi`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), "&", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match none of the following rules:\nFoo\n= abc\nall\nof:\nFoo\n= def\nFoo\n= ghi`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), "&", ("foo", "=", "def"), "!", ("foo", "=", "ghi")]`,
                result: `Match none of the following rules:\nFoo\n= abc\nall\nof:\nFoo\n= def\nFoo\n!= ghi`,
            },
        ];

        class Parent extends Component {
            setup() {
                this.state = useState({ domain: `[]` });
            }
        }
        Parent.components = { DomainSelector };
        Parent.template = xml`<DomainSelector resModel="'partner'" isDebugMode="true" domain="state.domain"/>`;

        const parent = await mountComponent(Parent);

        for (const { domain, result } of toTest) {
            parent.state.domain = domain;
            await nextTick();
            assert.strictEqual(target.querySelector(".o_domain_selector").innerText, result);
        }
    });

    QUnit.test("support properties", async (assert) => {
        assert.expect(7);

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
            { name: "xphone_prop_2", string: "P2", type: "selection", selection: [] },
        ];
        serverData.models.product.records[1].definitions = [
            { name: "xpad_prop_1", string: "P3", type: "many2one", relation: "partner" },
        ];

        let expectedDomain = `[("id", "=", 1)]`;

        class Parent extends Component {
            static template = xml`
                <DomainSelector
                    resModel="'partner'"
                    domain="domain"
                    readonly="false"
                    isDebugMode="true"
                    update="(domain) => this.onUpdate(domain)"
                />
            `;
            static components = { DomainSelector };
            setup() {
                this.domain = expectedDomain;
            }
            onUpdate(domain) {
                assert.strictEqual(domain, expectedDomain);
                this.domain = domain;
                this.render();
            }
        }

        await mountComponent(Parent);
        await openModelFieldSelectorPopover(target);
        await click(
            target,
            ".o_model_field_selector_popover_item[data-name='properties'] .o_model_field_selector_popover_relation_icon"
        );
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_value").textContent,
            "Properties"
        );

        expectedDomain = `[("properties.xphone_prop_2", "=", False)]`;
        await click(
            target.querySelector(
                ".o_model_field_selector_popover_item[data-name='xphone_prop_2'] button"
            )
        );
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_value").textContent,
            "PropertiesP2"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_domain_leaf_operator_select option")].map(
                (e) => e.value
            ),
            ["=", "!=", "set", "not_set"]
        );

        await openModelFieldSelectorPopover(target);
        expectedDomain = `[("properties.xpad_prop_1", "=", 1)]`;
        await click(
            target.querySelector(
                ".o_model_field_selector_popover_item[data-name='xpad_prop_1'] button"
            )
        );
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_value").textContent,
            "PropertiesP3"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_domain_leaf_operator_select option")].map(
                (e) => e.value
            ),
            ["=", "!=", "set", "not_set"]
        );
    });

    QUnit.test("no button 'New Rule' (readonly mode)", async (assert) => {
        await makeDomainSelector({
            readonly: true,
            domain: `[("bar", "=", True)]`,
        });
        assert.containsOnce(target, ".o_domain_leaf");
        assert.containsNone(target, "a[role=button]");
    });

    QUnit.test("button 'New Rule' (edit mode)", async (assert) => {
        await makeDomainSelector();
        assert.containsNone(target, ".o_domain_leaf");
        assert.containsOnce(target, "a[role=button]");

        await click(target, "a[role=button]");
        assert.containsOnce(target, ".o_domain_leaf");
        assert.containsOnce(target, "a[role=button]");

        await click(target, "a[role=button]");
        assert.containsN(target, ".o_domain_leaf", 2);
        assert.containsOnce(target, "a[role=button]");
    });

    QUnit.test("updating path should also update operator if invalid", async (assert) => {
        await mountComponent(DomainSelector, {
            props: {
                resModel: "partner",
                domain: `[("id", "<", 0)]`,
                readonly: false,
                update: (domain) => {
                    assert.strictEqual(domain, `[("foo", "=", "")]`);
                },
            },
        });

        await click(target, ".o_model_field_selector");
        await click(target, ".o_model_field_selector_popover_item[data-name=foo] button");
    });

    QUnit.test("treat false and true like False and True", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `[("bar","=",false)]`,
            readonly: true,
        });
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Bar is not set`);
        await parent.set(`[("bar","=",true)]`);
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Bar is set`);
    });

    QUnit.test("Edit the value for field char and an operator in", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `[("foo", "in", ["a", "b", uid])]`,
            update: (domain) => {
                assert.step(domain);
            },
        });
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "a",
            "b",
            "uid",
        ]);
        assert.deepEqual(
            [...target.querySelectorAll(".o_ds_value_cell .o_tag")].map((el) => el.dataset.color),
            ["0", "0", "2"]
        );
        assert.containsOnce(target, ".o_domain_leaf_value_input");

        await editInput(target, ".o_domain_leaf_value_input", "c");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "a",
            "b",
            "uid",
            "c",
        ]);
        assert.verifySteps([`[("foo", "in", ["a", "b", uid, "c"])]`]);

        await click(target.querySelectorAll(".o_tag .o_delete")[2]);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "a",
            "b",
            "c",
        ]);
        assert.verifySteps([`[("foo", "in", ["a", "b", "c"])]`]);

        await parent.set(`[("foo", "in", "a")]`);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "a",
        ]);

        await editInput(target, ".o_domain_leaf_value_input", "b");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "a",
            "b",
        ]);
        assert.verifySteps([`[("foo", "in", ["a", "b"])]`]);
    });

    QUnit.test("display of an unknown operator (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `[("foo", "hop", "a")]`,
            readonly: true,
        });
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Foo "hop" a`);

        await parent.set(`[("foo", hop, "a")]`);
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Foo hop a`);
    });

    QUnit.test("display of an unknown operator (edit)", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `[("foo", "hop", "a")]`,
        });
        assert.strictEqual(getSelectedOperator(target), `"hop"`);

        await parent.set(`[("foo", hop, "a")]`);
        assert.strictEqual(getSelectedOperator(target), `hop`);
    });

    QUnit.test("display of negation of an unknown operator (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `["!", ("foo", "hop", "a")]`,
            readonly: true,
        });
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Foo not "hop" a`);

        await parent.set(`["!", ("foo", hop, "a")]`);
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Foo not hop a`);
    });

    QUnit.test("display of an operator without negation defined (readonly)", async (assert) => {
        await makeDomainSelector({
            resModel: "partner",
            domain: `["!", ("foo", "=?", "a")]`,
            readonly: true,
        });
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Foo not =? a`);
    });

    QUnit.test("display of an operator without negation defined (edit)", async (assert) => {
        await makeDomainSelector({
            resModel: "partner",
            domain: `["!", ("foo", "=?", "a")]`,
        });
        assert.strictEqual(getSelectedOperator(target), `not =?`);
    });

    QUnit.test("display of a contextual value (readonly)", async (assert) => {
        await makeDomainSelector({
            domain: `[("foo", "=", uid)]`,
            readonly: true,
        });
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, `Foo = uid`);
    });

    QUnit.test("display of an operator without negation defined (edit)", async (assert) => {
        await makeDomainSelector({
            resModel: "partner",
            domain: `["!", (expr, "parent_of", "a")]`,
        });
        assert.strictEqual(getSelectedOperator(target), `not parent of`);
    });

    QUnit.test("boolean field (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        await parent.set(`[("bar", "=", True)]`);
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, "Bar is set");
        await parent.set(`[("bar", "=", False)]`);
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, "Bar is not set");
        await parent.set(`[("bar", "!=", True)]`);
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, "Bar is not set");
        await parent.set(`[("bar", "!=", False)]`);
        assert.strictEqual(
            target.querySelector(".o_domain_leaf").textContent,
            "Bar is not not set"
        );
    });

    QUnit.test("integer field (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        const toTest = [
            { domain: `[("int", "=", True)]`, text: `Integer = true` },
            { domain: `[("int", "=", False)]`, text: `Integer is not set ` },
            { domain: `[("int", "!=", True)]`, text: `Integer != true` },
            { domain: `[("int", "!=", False)]`, text: `Integer is set ` },
            { domain: `[("int", "=", 1)]`, text: `Integer = 1` },
            { domain: `[("int", "!=", 1)]`, text: `Integer != 1` },
            { domain: `[("int", "<", 1)]`, text: `Integer < 1` },
            { domain: `[("int", "<=", 1)]`, text: `Integer <= 1` },
            { domain: `[("int", ">", 1)]`, text: `Integer > 1` },
            { domain: `[("int", ">=", 1)]`, text: `Integer >= 1` },
            {
                domain: `["&", ("int", ">=", 1),("int","<=", 2)]`,
                text: `Integer is between 1 and 2`,
            },
        ];
        for (const { domain, text } of toTest) {
            await parent.set(domain);
            assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, text);
        }
    });

    QUnit.test("date field (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        const toTest = [
            { domain: `[("date", "=", False)]`, text: `Date is not set ` },
            { domain: `[("date", "!=", False)]`, text: `Date is set ` },
            { domain: `[("date", "=", "2023-07-03")]`, text: `Date = 2023-07-03` },
            { domain: `[("date", "=", context_today())]`, text: `Date = context_today()` },
            { domain: `[("date", "!=", "2023-07-03")]`, text: `Date != 2023-07-03` },
            { domain: `[("date", "<", "2023-07-03")]`, text: `Date < 2023-07-03` },
            { domain: `[("date", "<=", "2023-07-03")]`, text: `Date <= 2023-07-03` },
            { domain: `[("date", ">", "2023-07-03")]`, text: `Date > 2023-07-03` },
            { domain: `[("date", ">=", "2023-07-03")]`, text: `Date >= 2023-07-03` },
            {
                domain: `["&", ("date", ">=", "2023-07-03"),("date","<=", "2023-07-15")]`,
                text: `Date is between 2023-07-03 and 2023-07-15`,
            },
            {
                domain: `["&", ("date", ">=", "2023-07-03"),("date","<=", context_today())]`,
                text: `Date is between "2023-07-03" and context_today()`,
            },
        ];
        for (const { domain, text } of toTest) {
            await parent.set(domain);
            assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, text);
        }
    });

    QUnit.test("char field (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        const toTest = [
            { domain: `[("foo", "=", False)]`, text: `Foo is not set ` },
            { domain: `[("foo", "!=", False)]`, text: `Foo is set ` },
            { domain: `[("foo", "=", "abc")]`, text: `Foo = abc` },
            { domain: `[("foo", "=", expr)]`, text: `Foo = expr` },
            { domain: `[("foo", "!=", "abc")]`, text: `Foo != abc` },
            { domain: `[("foo", "ilike", "abc")]`, text: `Foo contains abc` },
            { domain: `[("foo", "not ilike", "abc")]`, text: `Foo does not contain abc` },
            { domain: `[("foo", "in", ["abc", "def"])]`, text: `Foo is in ( abc , def )` },
            { domain: `[("foo", "not in", ["abc", "def"])]`, text: `Foo is not in ( abc , def )` },
        ];
        for (const { domain, text } of toTest) {
            await parent.set(domain);
            assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, text);
        }
    });

    QUnit.test("selection field (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        const toTest = [
            { domain: `[("state", "=", False)]`, text: `State is not set ` },
            { domain: `[("state", "!=", False)]`, text: `State is set ` },
            { domain: `[("state", "=", "abc")]`, text: `State = ABC` },
            { domain: `[("state", "=", expr)]`, text: `State = expr` },
            { domain: `[("state", "!=", "abc")]`, text: `State != ABC` },
            { domain: `[("state", "in", ["abc", "def"])]`, text: `State is in ( ABC , DEF )` },
            {
                domain: `[("state", "not in", ["abc", "def"])]`,
                text: `State is not in ( ABC , DEF )`,
            },
            {
                domain: `[("state", "not in", ["abc", expr])]`,
                text: `State is not in ( "ABC" , expr )`,
            },
        ];
        for (const { domain, text } of toTest) {
            await parent.set(domain);
            assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, text);
        }
    });

    QUnit.test("selection property (readonly)", async (assert) => {
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
            {
                name: "selection_prop",
                string: "Selection",
                type: "selection",
                selection: [
                    ["abc", "ABC"],
                    ["def", "DEF"],
                ],
            },
        ];
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        const toTest = [
            {
                domain: `[("properties.selection_prop", "=", False)]`,
                text: `PropertiesSelection is not set `,
            },
            {
                domain: `[("properties.selection_prop", "!=", False)]`,
                text: `PropertiesSelection is set `,
            },
            {
                domain: `[("properties.selection_prop", "=", "abc")]`,
                text: `PropertiesSelection = ABC`,
            },
            {
                domain: `[("properties.selection_prop", "=", expr)]`,
                text: `PropertiesSelection = expr`,
            },
            {
                domain: `[("properties.selection_prop", "!=", "abc")]`,
                text: `PropertiesSelection != ABC`,
            },
        ];
        for (const { domain, text } of toTest) {
            await parent.set(domain);
            assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, text);
        }
    });

    QUnit.test("many2one field (readonly)", async (assert) => {
        const toTest = [
            {
                domain: `[("product_id", "=", 37)]`,
                text: "Product = xphone",
            },
            {
                domain: `[("product_id", "=", 2)]`,
                text: "Product = Inaccessible/missing record ID: 2",
            },
            {
                domain: `[("product_id", "!=", 37)]`,
                text: "Product != xphone",
            },
            {
                domain: `[("product_id", "=", False)]`,
                text: "Product = false",
            },
            {
                domain: `[("product_id", "!=", False)]`,
                text: "Product != false",
            },
            {
                domain: `[("product_id", "in", [])]`,
                text: "Product is in (  )",
            },
            {
                domain: `[("product_id", "in", [41, 37])]`,
                text: "Product is in ( xpad , xphone )",
            },
            {
                domain: `[("product_id", "in", [1, 37])]`,
                text: "Product is in ( Inaccessible/missing record ID: 1 , xphone )",
            },
            {
                domain: `[("product_id", "in", [1, uid, 37])]`,
                text: 'Product is in ( Inaccessible/missing record ID: 1 , uid , "xphone" )',
            },
            {
                domain: `[("product_id", "in", ["abc"])]`,
                text: "Product is in ( abc )",
            },
            {
                domain: `[("product_id", "in", 37)]`,
                text: "Product is in xphone",
            },
            {
                domain: `[("product_id", "in", 2)]`,
                text: "Product is in Inaccessible/missing record ID: 2",
            },
        ];
        const parent = await makeDomainSelector({ readonly: true });
        for (const { domain, text } of toTest) {
            await parent.set(domain);
            assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, text);
        }
    });

    QUnit.test("many2one field operators (edit)", async (assert) => {
        await makeDomainSelector({
            domain: `[("product_id", "=", false)]`,
        });
        assert.deepEqual(getOperatorOptions(target), [
            "is in",
            "is not in",
            "=",
            "!=",
            "contains",
            "does not contain",
            "is set",
            "is not set",
        ]);
    });

    QUnit.test("many2one field: operator switch (edit)", async (assert) => {
        await makeDomainSelector({
            domain: `[("product_id", "=", false)]`,
            update(domain) {
                assert.step(domain);
            },
        });
        await selectOperator(target, "in");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")),
            []
        );
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_id", "in", [])]`]);

        await selectOperator(target, "=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_id", "=", False)]`]);

        await selectOperator(target, "not in");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")),
            []
        );
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_id", "not in", [])]`]);

        await selectOperator(target, "ilike");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "");
        assert.verifySteps([`[("product_id", "ilike", "")]`]);

        await selectOperator(target, "!=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_id", "!=", False)]`]);

        await selectOperator(target, "not ilike");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "");
        assert.verifySteps([`[("product_id", "not ilike", "")]`]);
    });

    QUnit.test("many2one field and operator =/!= (edit)", async (assert) => {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_id", "=", False)]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getSelectedOperator(target), "=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([]);
        assert.containsNone(target, ".dropdown-menu");

        await editInput(target, ".o-autocomplete--input", "xph");

        assert.containsOnce(target, ".dropdown-menu");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".dropdown-menu li")), [
            "xphone",
        ]);
        assert.strictEqual(getSelectedOperator(target), "=");
        assert.strictEqual(getAutocompletValue(target), "xph");

        await click(target, ".dropdown-menu li");
        assert.strictEqual(getSelectedOperator(target), "=");
        assert.strictEqual(getAutocompletValue(target), "xphone");
        assert.verifySteps([`[("product_id", "=", 37)]`]);
        assert.containsNone(target, ".dropdown-menu");

        await editInput(target, ".o-autocomplete--input", "");
        assert.strictEqual(getSelectedOperator(target), "=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_id", "=", False)]`]);

        await selectOperator(target, "!=");
        assert.strictEqual(getSelectedOperator(target), "!=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_id", "!=", False)]`]);

        await editInput(target, ".o-autocomplete--input", "xpa");
        await click(target, ".dropdown-menu li");
        assert.strictEqual(getSelectedOperator(target), "!=");
        assert.strictEqual(getAutocompletValue(target), "xpad");
        assert.verifySteps([`[("product_id", "!=", 41)]`]);
    });

    QUnit.test("many2one field and operator in/not in (edit)", async (assert) => {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_id", "in", [37])]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getSelectedOperator(target), "is in");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "xphone",
        ]);
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([]);
        assert.containsNone(target, ".dropdown-menu");

        await editInput(target, ".o-autocomplete--input", "x");
        assert.containsOnce(target, ".dropdown-menu");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".dropdown-menu li")), [
            "xpad",
        ]);

        await click(target, ".dropdown-menu li");
        assert.verifySteps([`[("product_id", "in", [37, 41])]`]);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "xphone",
            "xpad",
        ]);
        assert.strictEqual(getAutocompletValue(target), "");

        await selectOperator(target, "not in");
        assert.strictEqual(getSelectedOperator(target), "is not in");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "xphone",
            "xpad",
        ]);
        assert.verifySteps([`[("product_id", "not in", [37, 41])]`]);

        await click(target.querySelector(".o_tag .o_delete"));
        assert.strictEqual(getSelectedOperator(target), "is not in");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "xpad",
        ]);
        assert.verifySteps([`[("product_id", "not in", [41])]`]);
    });

    QUnit.test("many2one field and operator ilike/not ilike (edit)", async (assert) => {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_id", "ilike", "abc")]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getSelectedOperator(target), "contains");
        assert.containsNone(target, ".o-autocomplete--input");
        assert.containsOnce(target, ".o_ds_value_cell .o_input");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "abc");
        assert.verifySteps([]);

        await editInput(target, ".o_ds_value_cell .o_input", "def");
        assert.strictEqual(getSelectedOperator(target), "contains");
        assert.containsOnce(target, ".o_ds_value_cell .o_input");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "def");
        assert.verifySteps([`[("product_id", "ilike", "def")]`]);

        await selectOperator(target, "not ilike");
        assert.strictEqual(getSelectedOperator(target), "does not contain");
        assert.containsOnce(target, ".o_ds_value_cell .o_input");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "def");
        assert.verifySteps([`[("product_id", "not ilike", "def")]`]);
    });

    QUnit.test("many2many field and operator set/not set (edit)", async (assert) => {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_id", "=", False)]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getSelectedOperator(target), "=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([]);

        await selectOperator(target, "not_set");

        assert.strictEqual(getSelectedOperator(target), "is not set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_id", "=", False)]`]);

        await selectOperator(target, "set");
        assert.strictEqual(getSelectedOperator(target), "is set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_id", "!=", False)]`]);

        await selectOperator(target, "!=");
        assert.strictEqual(getSelectedOperator(target), "!=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_id", "!=", False)]`]);
    });

    QUnit.test("many2many field: clone a set/not set condition", async (assert) => {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_id", "=", False)]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getSelectedOperator(target), "=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([]);

        await selectOperator(target, "not_set");
        assert.strictEqual(getSelectedOperator(target), "is not set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_id", "=", False)]`]);
        assert.containsOnce(target, ".o_domain_leaf");

        await click(target, ".o_domain_add_node_button .fa-plus");
        assert.containsN(target, ".o_domain_leaf", 2);
        assert.strictEqual(getSelectedOperator(target), "is not set");
        assert.strictEqual(getSelectedOperator(target, 1), "is not set");
        assert.verifySteps([`["&", ("product_id", "=", False), ("product_id", "=", False)]`]);
    });

    QUnit.test("x2many field operators (edit)", async (assert) => {
        addProductIds();
        await makeDomainSelector({
            domain: `[("product_ids", "=", false)]`,
        });
        assert.deepEqual(getOperatorOptions(target), [
            "is in",
            "is not in",
            "=",
            "!=",
            "contains",
            "does not contain",
            "is set",
            "is not set",
        ]);
    });

    QUnit.test("x2many field: operator switch (edit)", async (assert) => {
        addProductIds();
        await makeDomainSelector({
            domain: `[("product_ids", "=", false)]`,
            update(domain) {
                assert.step(domain);
            },
        });
        await selectOperator(target, "in");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")),
            []
        );
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_ids", "in", [])]`]);

        await selectOperator(target, "=");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")),
            []
        );
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_ids", "=", [])]`]);

        await selectOperator(target, "not in");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")),
            []
        );
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_ids", "not in", [])]`]);

        await selectOperator(target, "ilike");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "");
        assert.verifySteps([`[("product_ids", "ilike", "")]`]);

        await selectOperator(target, "not_set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_ids", "=", False)]`]);

        await selectOperator(target, "!=");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")),
            []
        );
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([`[("product_ids", "!=", [])]`]);

        await selectOperator(target, "not ilike");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "");
        assert.verifySteps([`[("product_ids", "not ilike", "")]`]);

        await selectOperator(target, "set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_ids", "!=", False)]`]);
    });

    QUnit.test("many2many field and operator =/!=/in/not in (edit)", async (assert) => {
        addProductIds();
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_ids", "in", [37])]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getSelectedOperator(target), "is in");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "xphone",
        ]);
        assert.strictEqual(getAutocompletValue(target), "");
        assert.verifySteps([]);
        assert.containsNone(target, ".dropdown-menu");

        await editInput(target, ".o-autocomplete--input", "x");
        assert.containsOnce(target, ".dropdown-menu");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".dropdown-menu li")), [
            "xpad",
        ]);

        await click(target, ".dropdown-menu li");
        assert.verifySteps([`[("product_ids", "in", [37, 41])]`]);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "xphone",
            "xpad",
        ]);
        assert.strictEqual(getAutocompletValue(target), "");

        await selectOperator(target, "not in");
        assert.strictEqual(getSelectedOperator(target), "is not in");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "xphone",
            "xpad",
        ]);
        assert.verifySteps([`[("product_ids", "not in", [37, 41])]`]);

        await click(target.querySelector(".o_tag .o_delete"));
        assert.strictEqual(getSelectedOperator(target), "is not in");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")), [
            "xpad",
        ]);
        assert.verifySteps([`[("product_ids", "not in", [41])]`]);

        await selectOperator(target, "=");
        assert.strictEqual(getSelectedOperator(target), "=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")),
            []
        ); // to improve -> should be [xpad]
        assert.verifySteps([`[("product_ids", "=", [])]`]);

        await selectOperator(target, "!=");
        assert.strictEqual(getSelectedOperator(target), "!=");
        assert.strictEqual(getAutocompletValue(target), "");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_ds_value_cell .o_tag")),
            []
        );
        assert.verifySteps([`[("product_ids", "!=", [])]`]);
    });

    QUnit.test("many2many field and operator ilike/not ilike (edit)", async (assert) => {
        addProductIds();
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_ids", "ilike", "abc")]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getSelectedOperator(target), "contains");
        assert.containsNone(target, ".o-autocomplete--input");
        assert.containsOnce(target, ".o_ds_value_cell .o_input");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "abc");
        assert.verifySteps([]);

        await editInput(target, ".o_ds_value_cell .o_input", "def");
        assert.strictEqual(getSelectedOperator(target), "contains");
        assert.containsOnce(target, ".o_ds_value_cell .o_input");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "def");
        assert.verifySteps([`[("product_ids", "ilike", "def")]`]);

        await selectOperator(target, "not ilike");
        assert.strictEqual(getSelectedOperator(target), "does not contain");
        assert.containsOnce(target, ".o_ds_value_cell .o_input");
        assert.strictEqual(target.querySelector(".o_ds_value_cell .o_input").value, "def");
        assert.verifySteps([`[("product_ids", "not ilike", "def")]`]);
    });

    QUnit.test("many2many field and operator set/not set (edit)", async (assert) => {
        addProductIds();
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_ids", "=", False)]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getSelectedOperator(target), "is not set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([]);

        await selectOperator(target, "set");
        assert.strictEqual(getSelectedOperator(target), "is set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_ids", "!=", False)]`]);
    });

    QUnit.test("Include archived button basic use", async (assert) => {
        serverData.models.partner.fields.active = {
            string: "Active",
            type: "boolean",
            searchable: true,
        };
        await makeDomainSelector({
            isDebugMode: true,
            domain: `["&", ("foo", "=", "test"), ("bar", "=", True)]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.containsN(target, ".o_domain_leaf", 2);
        assert.containsOnce(target, '.form-switch label:contains("Include archived")');
        await click(target, ".form-switch");
        assert.containsN(target, ".o_domain_leaf", 2);
        assert.verifySteps([
            '["&", "&", ("foo", "=", "test"), ("bar", "=", True), ("active", "in", [True, False])]',
        ]);
        await click(target, ".dropdown-toggle");
        await click(target, ".dropdown-menu span:nth-child(2)");
        assert.containsN(target, ".o_domain_leaf", 2);
        assert.verifySteps([
            '["&", "|", ("foo", "=", "test"), ("bar", "=", True), ("active", "in", [True, False])]',
        ]);
        await click(target, ".form-switch");
        assert.containsN(target, ".o_domain_leaf", 2);
        assert.verifySteps(['["|", ("foo", "=", "test"), ("bar", "=", True)]']);
    });

    QUnit.test("Include archived on empty tree", async (assert) => {
        serverData.models.partner.fields.active = {
            string: "Active",
            type: "boolean",
            searchable: true,
        };
        await makeDomainSelector({
            isDebugMode: true,
            domain: `[("foo", "=", "test")]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.containsOnce(target, ".o_domain_leaf");
        assert.containsOnce(target, '.form-switch label:contains("Include archived")');
        await click(target, ".form-switch");
        assert.containsOnce(target, ".o_domain_leaf");
        assert.verifySteps(['["&", ("foo", "=", "test"), ("active", "in", [True, False])]']);
        await click(target, ".o_domain_delete_node_button");
        assert.containsNone(target, ".o_domain_leaf");
        assert.verifySteps(['[("active", "in", [True, False])]']);
        await click(target, ".form-switch");
        assert.verifySteps(["[]"]);
        await click(target, ".form-switch");
        assert.containsNone(target, ".o_domain_leaf");
        assert.verifySteps(['[("active", "in", [True, False])]']);
        await click(target, "a[role=button]");
        assert.containsOnce(target, ".o_domain_leaf");
        assert.verifySteps(['["&", ("id", "=", 1), ("active", "in", [True, False])]']);
    });

    QUnit.test(
        "Include archived not shown when model doesn't have the active field",
        async (assert) => {
            await makeDomainSelector({
                isDebugMode: true,
                domain: `[("foo", "=", "test")]`,
                update(domain) {
                    assert.step(domain);
                },
            });
            assert.containsOnce(target, ".o_domain_leaf");
            assert.containsNone(target, '.form-switch label:contains("Include archived")');
        }
    );
});
