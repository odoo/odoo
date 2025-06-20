/** @odoo-module **/

import {
    click,
    editInput,
    getFixture,
    getNodesTextContent,
    mount,
    nextTick,
    patchDate,
    patchTimeZone,
    patchWithCleanup,
} from "../helpers/utils";
import { Component, useState, xml } from "@odoo/owl";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { fieldService } from "@web/core/field_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { makeTestEnv } from "../helpers/mock_env";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { getPickerApplyButton, getPickerCell } from "./datetime/datetime_test_helpers";
import { openModelFieldSelectorPopover } from "./model_field_selector_tests";
import { nameService } from "@web/core/name_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { browser } from "@web/core/browser/browser";
import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
import {
    SELECTORS as treeEditorSELECTORS,
    addNewRule,
    clearNotSupported,
    clickOnButtonAddBranch,
    clickOnButtonAddNewRule,
    clickOnButtonDeleteNode,
    editValue,
    getConditionText,
    getCurrentOperator,
    getCurrentPath,
    getCurrentValue,
    getOperatorOptions,
    isNotSupportedOperator,
    isNotSupportedPath,
    isNotSupportedValue,
    selectOperator,
    selectValue,
    toggleArchive,
    getValueOptions,
} from "./condition_tree_editor_helpers";

export {
    addNewRule,
    clearNotSupported,
    clickOnButtonAddBranch,
    clickOnButtonAddNewRule,
    clickOnButtonDeleteNode,
    editValue,
    getConditionText,
    getCurrentOperator,
    getCurrentPath,
    getCurrentValue,
    getOperatorOptions,
    isNotSupportedOperator,
    isNotSupportedPath,
    isNotSupportedValue,
    selectOperator,
    selectValue,
    toggleArchive,
} from "./condition_tree_editor_helpers";

export const SELECTORS = {
    ...treeEditorSELECTORS,
    debugArea: ".o_domain_selector_debug_container textarea",
    resetButton: ".o_domain_selector_row > button",
};
import { localization } from "@web/core/l10n/localization";

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

////////////////////////////////////////////////////////////////////////////////

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
        // As we gave an empty domain, there should be a visible button to add
        // the first domain part
        assert.containsOnce(target, SELECTORS.addNewRule);

        // Clicking on that button should add a visible field selector in the
        // component so that the user can change the field chain
        await addNewRule(target);
        assert.containsOnce(target, ".o_model_field_selector");

        // Focusing the field selector input should open a field selector popover
        await openModelFieldSelectorPopover(target);
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
        assert.containsOnce(target, SELECTORS.debugArea);
        assert.strictEqual(target.querySelector(SELECTORS.debugArea).value, `[("bar", "=", True)]`);
        // There should be a "+" button to add a domain part; clicking on it
        // should add the default "('id', '=', 1)" domain
        assert.containsOnce(target, SELECTORS.buttonAddNewRule);

        await clickOnButtonAddNewRule(target);
        assert.strictEqual(
            target.querySelector(SELECTORS.debugArea).value,
            `["&", ("bar", "=", True), ("bar", "=", True)]`
        );
        // There should be two "Add branch" buttons to add a domain "branch"; clicking on
        // the first one, should add this group with defaults "('id', '=', 1)"
        // domains and the "|" operator
        assert.containsN(target, SELECTORS.buttonAddBranch, 2);

        await clickOnButtonAddBranch(target);
        assert.strictEqual(
            target.querySelector(SELECTORS.debugArea).value,
            `["&", "&", ("bar", "=", True), "|", ("id", "=", 1), ("id", "=", 1), ("bar", "=", True)]`
        );
        // There should be five buttons to remove domain part; clicking on
        // the two last ones, should leave a domain with only the "bar" and
        // "foo" fields, with the initial "&" operator
        assert.containsN(target, SELECTORS.buttonDeleteNode, 5);

        await clickOnButtonDeleteNode(target, -1);
        await clickOnButtonDeleteNode(target, -1);
        assert.strictEqual(
            target.querySelector(SELECTORS.debugArea).value,
            `["&", ("bar", "=", True), ("id", "=", 1)]`
        );
    });

    QUnit.test("creating domain for binary field", async (assert) => {
        // Add a binary field to the server data
        serverData.models.partner.fields.image = {
            string: "Image",
            type: "binary",
            searchable: true,
        }

        await makeDomainSelector({
            isDebugMode: true,
        });

        // Add new rule to select field
        await addNewRule(target);
        await openModelFieldSelectorPopover(target);

        // Find and select the binary field
        const binaryFieldItem = [...document.querySelectorAll(".o_model_field_selector_popover_item_name")]
            .find(el => el.textContent.trim() === "Imageimage (binary)");
        assert.ok(binaryFieldItem, "binary field should be available in field selector");

        await click(binaryFieldItem);

        // Check that the operator options are limited to 'set' and 'not_set'
        const operators = getOperatorOptions(target).map(opt => opt?.textContent?.trim?.() ?? opt?.trim?.() ?? "");
        assert.deepEqual(operators, ["is set", "is not set"], "binary field should only allow set and not_set");

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
        assert.strictEqual(getCurrentPath(target), "fooooooo");
        assert.containsOnce(target, ".o_model_field_selector_warning");
        assert.strictEqual(
            target.querySelector(".o_model_field_selector_warning").title,
            "Invalid field chain"
        );
        assert.strictEqual(getOperatorOptions(target).length, 1);
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), `abc`);

        await openModelFieldSelectorPopover(target);
        await click(target.querySelector(".o_model_field_selector_popover_item_name"));
        assert.strictEqual(getCurrentPath(target), "Bar");
        assert.strictEqual(getCurrentOperator(target), "is");
        assert.strictEqual(getCurrentValue(target), "set");
    });

    QUnit.test("building a domain with an invalid path (2)", async (assert) => {
        await makeDomainSelector({
            domain: `[(bloup, "=", "abc")]`,
            update(domain) {
                assert.strictEqual(domain, `[("id", "=", 1)]`);
            },
        });
        assert.strictEqual(getCurrentPath(target), "bloup");
        assert.ok(isNotSupportedPath(target));
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), `abc`);

        await clearNotSupported(target);
        assert.strictEqual(getCurrentPath(target), "ID");
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "1");
    });

    QUnit.test("building a domain with an invalid operator", async (assert) => {
        await makeDomainSelector({
            domain: `[("foo", "!!!!=!!!!", "abc")]`,
            update(domain) {
                assert.strictEqual(domain, `[("foo", "=", "abc")]`);
            },
        });
        assert.strictEqual(getCurrentPath(target), "Foo");
        assert.containsNone(target, ".o_model_field_selector_warning");
        assert.strictEqual(getCurrentOperator(target), `"!!!!=!!!!"`);
        assert.ok(isNotSupportedOperator(target));
        assert.strictEqual(getCurrentValue(target), "abc");

        await clearNotSupported(target);
        assert.strictEqual(getCurrentPath(target), "Foo");
        assert.containsNone(target, ".o_model_field_selector_warning");
        assert.strictEqual(getOperatorOptions(target).length, 8);
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "abc");
    });

    QUnit.test("building a domain with an expression for value", async (assert) => {
        patchDate(2023, 3, 20, 17, 0, 0);
        await makeDomainSelector({
            domain: `[("datetime", ">=", context_today())]`,
            update(domain) {
                assert.strictEqual(domain, `[("datetime", ">=", "2023-04-20 16:00:00")]`);
            },
        });
        assert.strictEqual(getCurrentValue(target), "context_today()");

        await clearNotSupported(target);
        assert.strictEqual(getCurrentValue(target), "04/20/2023 17:00:00");
    });

    QUnit.test("building a domain with an expression in value", async (assert) => {
        await makeDomainSelector({
            domain: `[("int", "=", id)]`,
            update(domain) {
                assert.strictEqual(domain, `[("int", "<", 1)]`);
            },
        });
        assert.strictEqual(getCurrentPath(target), "Integer");
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "id");

        await selectOperator(target, "<");
        assert.strictEqual(getCurrentPath(target), "Integer");
        assert.strictEqual(getCurrentOperator(target), "<");
        assert.strictEqual(getCurrentValue(target), "1");
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
        assert.ok(isNotSupportedValue(target));

        await clearNotSupported(target);
        assert.verifySteps([`[("product_id", "ilike", "")]`]);

        await editInput(target, `${SELECTORS.valueEditor} input`, "pad");
        assert.verifySteps([`[("product_id", "ilike", "pad")]`]);
    });

    QUnit.test("editing a domain with `parent` key", async (assert) => {
        await makeDomainSelector({
            resModel: "product",
            domain: `[("name", "=", parent.foo)]`,
            isDebugMode: true,
        });
        assert.strictEqual(getCurrentValue(target), "parent.foo");
        assert.ok(isNotSupportedValue(target));
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
        assert.containsOnce(target, SELECTORS.condition);

        newDomain = `
            [
                ['product_id', 'ilike', 1],
                ['id', '=', 0]
            ]
        `;
        await editInput(target, SELECTORS.debugArea, newDomain);
        assert.strictEqual(
            target.querySelector(SELECTORS.debugArea).value,
            newDomain,
            "the domain should not have been formatted"
        );
        assert.containsN(target, SELECTORS.condition, 2);
    });

    QUnit.test(
        "set [(1, '=', 1)] or [(0, '=', 1)] as domain with the debug textarea",
        async (assert) => {
            assert.expect(11);

            let newDomain;
            await makeDomainSelector({
                domain: `[("product_id", "ilike", 1)]`,
                isDebugMode: true,
                update(domain, fromDebug) {
                    assert.strictEqual(domain, newDomain);
                    assert.ok(fromDebug);
                },
            });
            assert.containsOnce(target, SELECTORS.condition);

            newDomain = `[(1, "=", 1)]`;
            await editInput(target, SELECTORS.debugArea, newDomain);
            assert.strictEqual(
                target.querySelector(SELECTORS.debugArea).value,
                newDomain,
                "the domain should not have been formatted"
            );

            newDomain = `[(0, "=", 1)]`;
            await editInput(target, SELECTORS.debugArea, newDomain);
            assert.strictEqual(
                target.querySelector(SELECTORS.debugArea).value,
                newDomain,
                "the domain should not have been formatted"
            );
            assert.containsOnce(target, SELECTORS.condition);
            assert.strictEqual(getCurrentPath(target), "0");
            assert.strictEqual(getCurrentOperator(target), "=");
            assert.strictEqual(getCurrentValue(target), "1");
        }
    );

    QUnit.test("operator fallback (mode readonly)", async (assert) => {
        await makeDomainSelector({
            domain: `[['foo', 'like', 'kikou']]`,
            readonly: true,
        });
        assert.strictEqual(getConditionText(target), `Foo like kikou`);
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
        assert.strictEqual(getCurrentPath(target), "State");
        assert.strictEqual(getCurrentOperator(target), "is set");

        await selectOperator(target, "=");
        assert.strictEqual(getCurrentPath(target), "State");
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), `ABC`);
    });

    QUnit.test("show correct operator", async (assert) => {
        await makeDomainSelector({ domain: `[['state', 'in', ['abc']]]` });
        assert.strictEqual(getCurrentOperator(target), "is in");
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
        assert.strictEqual(comp.domain, `[("state", "in", ["a", "b", "c"])]`);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), [
            `a`,
            `b`,
            `c`,
        ]);
        assert.containsOnce(target, `${SELECTORS.valueEditor} select`);

        await click(target.querySelector(`${SELECTORS.valueEditor} .o_tag .o_delete`));
        assert.strictEqual(comp.domain, `[("state", "in", ["b", "c"])]`);

        await selectValue(target, "abc");
        assert.strictEqual(comp.domain, `[("state", "in", ["b", "c", "abc"])]`);
        const tags = target.querySelectorAll(SELECTORS.tag);
        assert.hasClass(tags[0], "o_tag_color_2");
        assert.hasClass(tags[1], "o_tag_color_2");
        assert.hasClass(tags[2], "o_tag_color_0");
    });

    QUnit.test("json field with operator change from 'equal' to 'ilike'", async (assert) => {
        await makeDomainSelector({ domain: `[['json_field', '=', "hey"]]` });
        assert.strictEqual(getCurrentPath(target), `Json Field`);
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), `hey`);

        await selectOperator(target, "ilike");
        assert.strictEqual(getCurrentOperator(target), "contains");
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
        assert.strictEqual(getCurrentValue(target), "-1");
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
        assert.strictEqual(getCurrentValue(target), "3 - 1");
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
        assert.containsNone(target, SELECTORS.resetButton);
        assert.containsNone(target, SELECTORS.debugArea);
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
        assert.containsNone(target, SELECTORS.resetButton);
        assert.containsOnce(target, SELECTORS.debugArea);
        assert.ok(target.querySelector(SELECTORS.debugArea).hasAttribute("readonly"));
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
        assert.containsOnce(target, SELECTORS.resetButton);
        assert.containsNone(target, SELECTORS.debugArea);
    });

    QUnit.test("domain not supported (mode edit + mode debug)", async (assert) => {
        await makeDomainSelector({
            domain: `[`,
            isDebugMode: true,
        });
        assert.containsOnce(target, SELECTORS.resetButton);
        assert.containsOnce(target, SELECTORS.debugArea);
        assert.notOk(target.querySelector(SELECTORS.debugArea).hasAttribute("readonly"));
    });

    QUnit.test("reset domain", async (assert) => {
        await makeDomainSelector({
            domain: `[`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(
            target.querySelector(".o_domain_selector").innerText.toLowerCase(),
            "this domain is not supported.\nreset domain"
        );
        assert.containsOnce(target, SELECTORS.resetButton);
        assert.containsNone(target, SELECTORS.addNewRule);

        await click(target, SELECTORS.resetButton);
        assert.strictEqual(
            target.querySelector(".o_domain_selector").innerText.toLowerCase(),
            "match all records\nnew rule"
        );
        assert.containsNone(target, SELECTORS.resetButton);
        assert.containsOnce(target, SELECTORS.addNewRule);
        assert.verifySteps(["[]"]);
    });

    QUnit.test("default condition depends on available fields", async (assert) => {
        serverData.models.partner.fields = {
            ...serverData.models.partner.fields,
            user_id: { string: "User", type: "many2one", relation: "user" },
        };
        await makeDomainSelector({
            domain: `[]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(
            target.querySelector(".o_domain_selector").innerText.toLowerCase(),
            "match all records\nnew rule"
        );
        await addNewRule(target);
        assert.verifySteps(['[("user_id", "in", [])]']);
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
        assert.verifySteps([`[("a", "=", 1)]`]);
        assert.strictEqual(getCurrentPath(target), "a");
        assert.containsOnce(target, ".o_model_field_selector_warning");
        assert.strictEqual(getOperatorOptions(target).length, 1);
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "1");
        assert.strictEqual(target.querySelector(SELECTORS.debugArea).value, `[("a", "=", 1)]`);
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

        assert.containsOnce(target, SELECTORS.condition);
        assert.strictEqual(getCurrentOperator(target), "is between");
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
        assert.containsN(target, SELECTORS.condition, 2);
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentOperator(target, 1), "is between");
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
        assert.containsN(target, SELECTORS.condition, 2);
        assert.strictEqual(getCurrentOperator(target), "is between");
        assert.strictEqual(getCurrentOperator(target, 1), "=");
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
        assert.containsN(target, SELECTORS.condition, 2);
        assert.strictEqual(getCurrentOperator(target), "is between");
        assert.strictEqual(getCurrentOperator(target, 1), "=");
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
            `Match\nany\nof the following rules:\ncreate_date\nis between\n2023-04-01 00:00:00\nand\n2023-04-30 23:59:59\n0\n=\n1`
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
        assert.containsOnce(target, SELECTORS.condition);
        assert.strictEqual(getCurrentOperator(target), "is between");
        assert.containsOnce(target, SELECTORS.valueEditor);
        assert.containsN(target.querySelector(SELECTORS.valueEditor), SELECTORS.editor, 2);
        assert.containsOnce(
            target.querySelector(SELECTORS.valueEditor),
            `${SELECTORS.editor} ${SELECTORS.clearNotSupported}`
        );
        assert.containsOnce(
            target.querySelector(SELECTORS.valueEditor),
            `${SELECTORS.editor} .o_datetime_input`
        );

        await clearNotSupported(target);
        assert.containsOnce(target, SELECTORS.valueEditor);
        assert.containsN(
            target.querySelector(SELECTORS.valueEditor),
            `${SELECTORS.editor} .o_datetime_input`,
            2
        );
        assert.verifySteps([
            `["&", ("datetime", ">=", "2023-01-01 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00")]`,
        ]);
    });

    QUnit.test("support of connector '!' (mode readonly)", async (assert) => {
        const toTest = [
            {
                domain: `["!", ("foo", "=", "abc")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc`,
            },
            {
                domain: `["!", "!", ("foo", "=", "abc")]`,
                result: `Match\nall\nof the following rules:\nFoo\n=\nabc`,
            },
            {
                domain: `["!", "!", "!", ("foo", "=", "abc")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc`,
            },
            {
                domain: `["!", "&", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nany\nof the following rules:\nFoo\n!=\nabc\nFoo\n!=\ndef`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc\nFoo\n!=\ndef`,
            },
            {
                domain: `["&", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["&", "!", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nall\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["&", ("foo", "=", "abc"), "!", ("foo", "=", "def")]`,
                result: `Match\nall\nof the following rules:\nFoo\n=\nabc\nFoo\n!=\ndef`,
            },
            {
                domain: `["&", ("foo", "=", "abc"), "!", "!", ("foo", "=", "def")]`,
                result: `Match\nall\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["|", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nany\nof the following rules:\nFoo\n!=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["|", "!", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nany\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["|", ("foo", "=", "abc"), "!", ("foo", "=", "def")]`,
                result: `Match\nany\nof the following rules:\nFoo\n=\nabc\nFoo\n!=\ndef`,
            },
            {
                domain: `["|", ("foo", "=", "abc"), "!", "!", ("foo", "=", "def")]`,
                result: `Match\nany\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["&", "!", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nall\nof the following rules:\nany\nof:\nFoo\n!=\nabc\nFoo\n!=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["&", "!", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc\nFoo\n!=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["|", "!", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nany\nof the following rules:\nFoo\n!=\nabc\nFoo\n!=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["|", "!", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nany\nof the following rules:\nall\nof:\nFoo\n!=\nabc\nFoo\n!=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["!", "&", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nany\nof the following rules:\nFoo\n!=\nabc\nFoo\n!=\ndef\nFoo\n!=\nghi`,
            },
            {
                domain: `["!", "|", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc\nFoo\n!=\ndef\nFoo\n!=\nghi`,
            },
            {
                domain: `["!", "&", "|", ("foo", "=", "abc"), "!", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nany\nof the following rules:\nall\nof:\nFoo\n!=\nabc\nFoo\n=\ndef\nFoo\n!=\nghi`,
            },
            {
                domain: `["!", "|", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nall\nof the following rules:\nany\nof:\nFoo\n!=\nabc\nFoo\n!=\ndef\nFoo\n!=\nghi`,
            },
            {
                domain: `["!", "&", ("foo", "=", "abc"), "|", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nany\nof the following rules:\nFoo\n!=\nabc\nall\nof:\nFoo\n!=\ndef\nFoo\n!=\nghi`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), "&", ("foo", "=", "def"), ("foo", "!=", "ghi")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc\nany\nof:\nFoo\n!=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), "&", ("foo", "!=", "def"), "!", ("foo", "=", "ghi")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc\nany\nof:\nFoo\n=\ndef\nFoo\n=\nghi`,
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
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc`,
            },
            {
                domain: `["!", "!", ("foo", "=", "abc")]`,
                result: `Match\nall\nof the following rules:\nFoo\n=\nabc`,
            },
            {
                domain: `["!", "!", "!", ("foo", "=", "abc")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc`,
            },
            {
                domain: `["!", "&", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nnot all\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nnone\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["&", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nall\nof the following rules:\nFoo\n!=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["&", "!", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nall\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["&", ("foo", "=", "abc"), "!", ("foo", "=", "def")]`,
                result: `Match\nall\nof the following rules:\nFoo\n=\nabc\nFoo\n!=\ndef`,
            },
            {
                domain: `["&", ("foo", "=", "abc"), "!", "!", ("foo", "=", "def")]`,
                result: `Match\nall\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["|", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nany\nof the following rules:\nFoo\n!=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["|", "!", "!", ("foo", "=", "abc"), ("foo", "=", "def")]`,
                result: `Match\nany\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["|", ("foo", "=", "abc"), "!", ("foo", "=", "def")]`,
                result: `Match\nany\nof the following rules:\nFoo\n=\nabc\nFoo\n!=\ndef`,
            },
            {
                domain: `["|", ("foo", "=", "abc"), "!", "!", ("foo", "=", "def")]`,
                result: `Match\nany\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef`,
            },
            {
                domain: `["&", "!", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nall\nof the following rules:\nnot all\nof:\nFoo\n=\nabc\nFoo\n=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["&", "!", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nall\nof the following rules:\nnone\nof:\nFoo\n=\nabc\nFoo\n=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["|", "!", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nany\nof the following rules:\nnot all\nof:\nFoo\n=\nabc\nFoo\n=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["|", "!", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nany\nof the following rules:\nnone\nof:\nFoo\n=\nabc\nFoo\n=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["!", "&", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nnot all\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["!", "|", "|", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nnone\nof the following rules:\nFoo\n=\nabc\nFoo\n=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["!", "&", "|", ("foo", "=", "abc"), "!", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nnot all\nof the following rules:\nany\nof:\nFoo\n=\nabc\nFoo\n!=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["!", "|", "&", ("foo", "=", "abc"), ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nnone\nof the following rules:\nall\nof:\nFoo\n=\nabc\nFoo\n=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["!", "&", ("foo", "=", "abc"), "|", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nnot all\nof the following rules:\nFoo\n=\nabc\nany\nof:\nFoo\n=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), "&", ("foo", "=", "def"), ("foo", "=", "ghi")]`,
                result: `Match\nnone\nof the following rules:\nFoo\n=\nabc\nall\nof:\nFoo\n=\ndef\nFoo\n=\nghi`,
            },
            {
                domain: `["!", "|", ("foo", "=", "abc"), "&", ("foo", "=", "def"), "!", ("foo", "=", "ghi")]`,
                result: `Match\nnone\nof the following rules:\nFoo\n=\nabc\nall\nof:\nFoo\n=\ndef\nFoo\n!=\nghi`,
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
        assert.expect(25);
        patchDate(2023, 9, 5, 15, 0, 0);

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
            { name: "xphone_prop_1", string: "Boolean", type: "boolean" },
            { name: "xphone_prop_2", string: "Selection", type: "selection", selection: [] },
            { name: "xphone_prop_3", string: "Char", type: "char" },
            { name: "xphone_prop_4", string: "Integer", type: "integer" },
            { name: "xphone_prop_5", string: "Date", type: "date" },
            { name: "xphone_prop_6", string: "Tags", type: "tags" },
            { name: "xphone_prop_7", string: "M2M", type: "many2many", comodel: "partner" },
        ];
        serverData.models.product.records[1].definitions = [
            { name: "xpad_prop_1", string: "M2O", type: "many2one", comodel: "partner" },
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
        assert.strictEqual(getCurrentPath(target), "Properties");
        expectedDomain = `[("properties.xpad_prop_1", "=", False)]`;
        await click(
            target.querySelector(
                ".o_model_field_selector_popover_item[data-name='xpad_prop_1'] button"
            )
        );
        assert.strictEqual(getCurrentPath(target), "Properties > M2O");
        assert.deepEqual(getOperatorOptions(target), ["=", "!=", "is set", "is not set"]);

        const toTests = [
            {
                name: "xphone_prop_1",
                domain: `[("properties.xphone_prop_1", "=", True)]`,
                options: ["is", "is not"],
            },
            {
                name: "xphone_prop_2",
                domain: `[("properties.xphone_prop_2", "=", False)]`,
                options: ["=", "!=", "is set", "is not set"],
            },
            {
                name: "xphone_prop_3",
                domain: `[("properties.xphone_prop_3", "=", "")]`,
                options: [
                    "=",
                    "!=",
                    "contains",
                    "does not contain",
                    "is in",
                    "is not in",
                    "is set",
                    "is not set",
                ],
            },
            {
                name: "xphone_prop_4",
                domain: `[("properties.xphone_prop_4", "=", 1)]`,
                options: [
                    "=",
                    "!=",
                    ">",
                    ">=",
                    "<",
                    "<=",
                    "is between",
                    "contains",
                    "does not contain",
                    "is set",
                    "is not set",
                ],
            },
            {
                name: "xphone_prop_5",
                domain: `[("properties.xphone_prop_5", "=", "2023-10-05")]`,
                options: ["=", "!=", ">", ">=", "<", "<=", "is between", "is set", "is not set"],
            },
            {
                name: "xphone_prop_6",
                domain: `[("properties.xphone_prop_6", "in", "")]`,
                options: ["is in", "is not in", "is set", "is not set"],
            },
            {
                name: "xphone_prop_7",
                domain: `[("properties.xphone_prop_7", "in", [])]`,
                options: ["is in", "is not in", "is set", "is not set"],
            },
        ];

        for (const { name, domain, options } of toTests) {
            await openModelFieldSelectorPopover(target);
            expectedDomain = domain;
            await click(
                target.querySelector(
                    `.o_model_field_selector_popover_item[data-name='${name}'] button`
                )
            );
            const { string } = serverData.models.product.records[0].definitions.find(
                (def) => def.name === name
            );
            assert.strictEqual(getCurrentPath(target), `Properties > ${string}`);
            assert.deepEqual(getOperatorOptions(target), options);
        }
    });

    QUnit.test("support properties (mode readonly)", async (assert) => {
        patchWithCleanup(localization, {
            dateFormat: `dd|MM|yyyy`,
        });
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
            { name: "xphone_prop_1", string: "Boolean", type: "boolean" },
            {
                name: "xphone_prop_2",
                string: "Selection",
                type: "selection",
                selection: [["abc", "ABC"]],
            },
            { name: "xphone_prop_3", string: "Char", type: "char" },
            { name: "xphone_prop_4", string: "Integer", type: "integer" },
            { name: "xphone_prop_5", string: "Date", type: "date" },
            { name: "xphone_prop_6", string: "Tags", type: "tags" },
            { name: "xphone_prop_7", string: "M2M", type: "many2many", comodel: "product" },
        ];
        serverData.models.product.records[1].definitions = [
            { name: "xpad_prop_1", string: "M2O", type: "many2one", comodel: "product" },
        ];

        const toTest = [
            {
                domain: `[("properties.xphone_prop_1", "=", False)]`,
                result: `PropertiesBoolean is not set`,
            },
            {
                domain: `[("properties.xphone_prop_2", "=", "abc")]`,
                result: `PropertiesSelection = ABC`,
            },
            {
                domain: `[("properties.xphone_prop_3", "=", "def")]`,
                result: `PropertiesChar = def`,
            },
            {
                domain: `[("properties.xphone_prop_4", "=", 1)]`,
                result: `PropertiesInteger = 1`,
            },
            {
                domain: `[("properties.xphone_prop_5", "=", "2023-10-05")]`,
                result: `PropertiesDate = 05|10|2023`,
            },
            {
                domain: `[("properties.xphone_prop_6", "in", "g")]`,
                result: `PropertiesTags is in g`,
            },
            {
                domain: `[("properties.xphone_prop_7", "in", [37])]`,
                result: `PropertiesM2M is in ( xphone )`,
            },
            {
                domain: `[("properties.xpad_prop_1", "=", 41)]`,
                result: `PropertiesM2O = xpad`,
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
            assert.strictEqual(getConditionText(target), result);
        }
    });

    QUnit.test("no button 'New Rule' (mode readonly)", async (assert) => {
        await makeDomainSelector({
            readonly: true,
            domain: `[("bar", "=", True)]`,
        });
        assert.containsOnce(target, SELECTORS.condition);
        assert.containsNone(target, "a[role=button]");
    });

    QUnit.test("button 'New Rule' (edit mode)", async (assert) => {
        await makeDomainSelector();
        assert.containsNone(target, SELECTORS.condition);
        assert.containsOnce(target, SELECTORS.addNewRule);

        await addNewRule(target);
        assert.containsOnce(target, SELECTORS.condition);
        assert.containsOnce(target, SELECTORS.addNewRule);

        await addNewRule(target);
        assert.containsN(target, SELECTORS.condition, 2);
        assert.containsOnce(target, SELECTORS.addNewRule);
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

        await openModelFieldSelectorPopover(target);
        await click(target, ".o_model_field_selector_popover_item[data-name=foo] button");
    });

    QUnit.test("treat false and true like False and True", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `[("bar","=",false)]`,
            readonly: true,
        });
        assert.strictEqual(getConditionText(target), `Bar is not set`);
        await parent.set(`[("bar","=",true)]`);
        assert.strictEqual(getConditionText(target), `Bar is set`);
    });

    QUnit.test("Edit the value for field char and an operator in", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `[("foo", "in", ["a", "b", uid])]`,
            update: (domain) => {
                assert.step(domain);
            },
            isDebugMode: true,
        });
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), [
            `"a"`,
            `"b"`,
            `uid`,
        ]);
        assert.deepEqual(
            [...target.querySelectorAll(SELECTORS.tag)].map((el) => el.dataset.color),
            ["0", "0", "2"]
        );

        await editValue(target, "c");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), [
            `"a"`,
            `"b"`,
            `uid`,
            `"c"`,
        ]);
        assert.verifySteps([`[("foo", "in", ["a", "b", uid, "c"])]`]);

        await click(target.querySelectorAll(".o_tag .o_delete")[2]);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), [
            `a`,
            `b`,
            `c`,
        ]);
        assert.verifySteps([`[("foo", "in", ["a", "b", "c"])]`]);

        await parent.set(`[("foo", "in", ["a"])]`);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), [`a`]);

        await editValue(target, "b");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), [`a`, `b`]);
        assert.verifySteps([`[("foo", "in", ["a", "b"])]`]);
    });

    QUnit.test("display of an unknown operator (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `[("foo", "hop", "a")]`,
            readonly: true,
        });
        assert.strictEqual(getConditionText(target), `Foo "hop" a`);

        await parent.set(`[("foo", hop, "a")]`);
        assert.strictEqual(getConditionText(target), `Foo hop a`);
    });

    QUnit.test("display of an unknown operator (edit)", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `[("foo", "hop", "a")]`,
        });
        assert.strictEqual(getCurrentOperator(target), `"hop"`);

        await parent.set(`[("foo", hop, "a")]`);
        assert.strictEqual(getCurrentOperator(target), `hop`);
    });

    QUnit.test("display of negation of an unknown operator (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            resModel: "partner",
            domain: `["!", ("foo", "hop", "a")]`,
            readonly: true,
        });
        assert.strictEqual(getConditionText(target), `Foo not "hop" a`);

        await parent.set(`["!", ("foo", hop, "a")]`);
        assert.strictEqual(getConditionText(target), `Foo not hop a`);
    });

    QUnit.test("display of an operator without negation defined (readonly)", async (assert) => {
        await makeDomainSelector({
            resModel: "partner",
            domain: `["!", ("foo", "=?", "a")]`,
            readonly: true,
        });
        assert.strictEqual(getConditionText(target), `Foo not =? a`);
    });

    QUnit.test("display of an operator without negation defined (edit)", async (assert) => {
        await makeDomainSelector({
            resModel: "partner",
            domain: `["!", ("foo", "=?", "a")]`,
        });
        assert.strictEqual(getCurrentOperator(target), `not =?`);
    });

    QUnit.test("display of a contextual value (readonly)", async (assert) => {
        await makeDomainSelector({
            domain: `[("foo", "=", uid)]`,
            readonly: true,
        });
        assert.strictEqual(getConditionText(target), `Foo = uid`);
    });

    QUnit.test("display of an operator without negation defined (edit)", async (assert) => {
        await makeDomainSelector({
            resModel: "partner",
            domain: `["!", (expr, "parent_of", "a")]`,
        });
        assert.strictEqual(getCurrentOperator(target), `not parent of`);
    });

    QUnit.test("boolean field (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        await parent.set(`[("bar", "=", True)]`);
        assert.strictEqual(getConditionText(target), "Bar is set");
        await parent.set(`[("bar", "=", False)]`);
        assert.strictEqual(getConditionText(target), "Bar is not set");
        await parent.set(`[("bar", "!=", True)]`);
        assert.strictEqual(getConditionText(target), "Bar is not set");
        await parent.set(`[("bar", "!=", False)]`);
        assert.strictEqual(getConditionText(target), "Bar is not not set");
    });

    QUnit.test("integer field (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        const toTest = [
            { domain: `[("int", "=", True)]`, text: `Integer = true` },
            { domain: `[("int", "=", False)]`, text: `Integer is not set` },
            { domain: `[("int", "!=", True)]`, text: `Integer != true` },
            { domain: `[("int", "!=", False)]`, text: `Integer is set` },
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
            assert.strictEqual(getConditionText(target), text);
        }
    });

    QUnit.test("date field (readonly)", async (assert) => {
        patchWithCleanup(localization, {
            dateFormat: `dd|MM|yyyy`,
        });
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        const toTest = [
            { domain: `[("date", "=", False)]`, text: `Date = false` },
            { domain: `[("date", "!=", False)]`, text: `Date != false` },
            { domain: `[("date", "=", "2023-07-03")]`, text: `Date = 03|07|2023` },
            { domain: `[("date", "=", context_today())]`, text: `Date = context_today()` },
            { domain: `[("date", "!=", "2023-07-03")]`, text: `Date != 03|07|2023` },
            { domain: `[("date", "<", "2023-07-03")]`, text: `Date < 03|07|2023` },
            { domain: `[("date", "<=", "2023-07-03")]`, text: `Date <= 03|07|2023` },
            { domain: `[("date", ">", "2023-07-03")]`, text: `Date > 03|07|2023` },
            { domain: `[("date", ">=", "2023-07-03")]`, text: `Date >= 03|07|2023` },
            {
                domain: `["&", ("date", ">=", "2023-07-03"),("date","<=", "2023-07-15")]`,
                text: `Date is between 03|07|2023 and 15|07|2023`,
            },
            {
                domain: `["&", ("date", ">=", "2023-07-03"),("date","<=", context_today())]`,
                text: `Date is between 03|07|2023 and context_today()`,
            },
        ];
        for (const { domain, text } of toTest) {
            await parent.set(domain);
            assert.strictEqual(getConditionText(target), text);
        }
    });

    QUnit.test("char field (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        const toTest = [
            { domain: `[("foo", "=", False)]`, text: `Foo is not set` },
            { domain: `[("foo", "!=", False)]`, text: `Foo is set` },
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
            assert.strictEqual(getConditionText(target), text);
        }
    });

    QUnit.test("selection field (readonly)", async (assert) => {
        const parent = await makeDomainSelector({
            readonly: true,
            domain: `[]`,
        });
        const toTest = [
            { domain: `[("state", "=", False)]`, text: `State is not set` },
            { domain: `[("state", "!=", False)]`, text: `State is set` },
            { domain: `[("state", "=", "abc")]`, text: `State = ABC` },
            { domain: `[("state", "=", expr)]`, text: `State = expr` },
            { domain: `[("state", "!=", "abc")]`, text: `State != ABC` },
            { domain: `[("state", "in", ["abc", "def"])]`, text: `State is in ( ABC , DEF )` },
            { domain: `[("state", "in", ["abc", False])]`, text: `State is in ( "ABC" , false )` },
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
            assert.strictEqual(getConditionText(target), text);
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
                text: `PropertiesSelection is not set`,
            },
            {
                domain: `[("properties.selection_prop", "!=", False)]`,
                text: `PropertiesSelection is set`,
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
            assert.strictEqual(getConditionText(target), text);
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
                text: "Product is in ( )",
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
            assert.strictEqual(getConditionText(target), text);
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
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), []);
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_id", "in", [])]`]);

        await selectOperator(target, "=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_id", "=", False)]`]);

        await selectOperator(target, "not in");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), []);
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_id", "not in", [])]`]);

        await selectOperator(target, "ilike");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_id", "ilike", "")]`]);

        await selectOperator(target, "!=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_id", "!=", False)]`]);

        await selectOperator(target, "not ilike");
        assert.strictEqual(getCurrentValue(target), "");
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
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([]);
        assert.containsNone(target, ".dropdown-menu");

        await editValue(target, "xph");

        assert.containsOnce(target, ".dropdown-menu");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".dropdown-menu li")), [
            "xphone",
        ]);
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "xph");

        await click(target, ".dropdown-menu li");
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "xphone");
        assert.verifySteps([`[("product_id", "=", 37)]`]);
        assert.containsNone(target, ".dropdown-menu");

        await editValue(target, "");
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_id", "=", False)]`]);

        await selectOperator(target, "!=");
        assert.strictEqual(getCurrentOperator(target), "!=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_id", "!=", False)]`]);

        await editValue(target, "xpa");
        await click(target, ".dropdown-menu li");
        assert.strictEqual(getCurrentOperator(target), "!=");
        assert.strictEqual(getCurrentValue(target), "xpad");
        assert.verifySteps([`[("product_id", "!=", 41)]`]);
    });

    QUnit.test("many2one field on record with falsy display_name", async (assert) => {
        serverData.models.product.records[0].display_name = false;

        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_id", "=", False)]`,
        });
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.containsNone(target, ".dropdown-menu");

        await click(target, ".o-autocomplete--input");

        assert.strictEqual(
            target.querySelector("a.dropdown-item").text,
            "Unnamed",
            "should have a Unnamed as fallback of many2one display_name"
        );
    });

    QUnit.test("many2one field and operator in/not in (edit)", async (assert) => {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        await makeDomainSelector({
            domain: `[("product_id", "in", [37])]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getCurrentOperator(target), "is in");
        assert.strictEqual(getCurrentValue(target), "xphone");
        assert.verifySteps([]);
        assert.containsNone(target, ".dropdown-menu");

        await editValue(target, "x");
        assert.containsOnce(target, ".dropdown-menu");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".dropdown-menu li")), [
            "xpad",
        ]);

        await click(target, ".dropdown-menu li");
        assert.verifySteps([`[("product_id", "in", [37, 41])]`]);
        assert.strictEqual(getCurrentValue(target), "xphone xpad");

        await selectOperator(target, "not in");
        assert.strictEqual(getCurrentOperator(target), "is not in");
        assert.strictEqual(getCurrentValue(target), "xphone xpad");
        assert.verifySteps([`[("product_id", "not in", [37, 41])]`]);

        await click(target.querySelector(".o_tag .o_delete"));
        assert.strictEqual(getCurrentOperator(target), "is not in");
        assert.strictEqual(getCurrentValue(target), "xpad");
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
        assert.strictEqual(getCurrentOperator(target), "contains");
        assert.containsNone(target, ".o-autocomplete--input");
        assert.containsOnce(target, `${SELECTORS.valueEditor} .o_input`);
        assert.strictEqual(getCurrentValue(target), "abc");
        assert.verifySteps([]);

        await editInput(target, `${SELECTORS.valueEditor} .o_input`, "def");
        assert.strictEqual(getCurrentOperator(target), "contains");
        assert.containsOnce(target, `${SELECTORS.valueEditor} .o_input`);
        assert.strictEqual(getCurrentValue(target), "def");
        assert.verifySteps([`[("product_id", "ilike", "def")]`]);

        await selectOperator(target, "not ilike");
        assert.strictEqual(getCurrentOperator(target), "does not contain");
        assert.containsOnce(target, `${SELECTORS.valueEditor} .o_input`);
        assert.strictEqual(getCurrentValue(target), "def");
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
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([]);

        await selectOperator(target, "not_set");

        assert.strictEqual(getCurrentOperator(target), "is not set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_id", "=", False)]`]);

        await selectOperator(target, "set");
        assert.strictEqual(getCurrentOperator(target), "is set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_id", "!=", False)]`]);

        await selectOperator(target, "!=");
        assert.strictEqual(getCurrentOperator(target), "!=");
        assert.strictEqual(getCurrentValue(target), "");
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
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([]);

        await selectOperator(target, "not_set");
        assert.strictEqual(getCurrentOperator(target), "is not set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_id", "=", False)]`]);
        assert.containsOnce(target, SELECTORS.condition);

        await clickOnButtonAddNewRule(target);
        assert.containsN(target, SELECTORS.condition, 2);
        assert.strictEqual(getCurrentOperator(target), "is not set");
        assert.strictEqual(getCurrentOperator(target, 1), "is not set");
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
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), []);
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_ids", "in", [])]`]);

        await selectOperator(target, "=");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), []);
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_ids", "=", [])]`]);

        await selectOperator(target, "not in");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), []);
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_ids", "not in", [])]`]);

        await selectOperator(target, "ilike");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_ids", "ilike", "")]`]);

        await selectOperator(target, "not_set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([`[("product_ids", "=", False)]`]);

        await selectOperator(target, "!=");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(SELECTORS.tag)), []);
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("product_ids", "!=", [])]`]);

        await selectOperator(target, "not ilike");
        assert.strictEqual(getCurrentValue(target), "");
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
        assert.strictEqual(getCurrentOperator(target), "is in");
        assert.strictEqual(getCurrentValue(target), "xphone");
        assert.verifySteps([]);
        assert.containsNone(target, ".dropdown-menu");

        await editValue(target, "x");
        assert.containsOnce(target, ".dropdown-menu");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".dropdown-menu li")), [
            "xpad",
        ]);

        await click(target, ".dropdown-menu li");
        assert.verifySteps([`[("product_ids", "in", [37, 41])]`]);
        assert.strictEqual(getCurrentValue(target), "xphone xpad");

        await selectOperator(target, "not in");
        assert.strictEqual(getCurrentOperator(target), "is not in");
        assert.strictEqual(getCurrentValue(target), "xphone xpad");
        assert.verifySteps([`[("product_ids", "not in", [37, 41])]`]);

        await click(target.querySelector(".o_tag .o_delete"));

        assert.strictEqual(getCurrentOperator(target), "is not in");
        assert.strictEqual(getCurrentValue(target), "xpad");
        assert.verifySteps([`[("product_ids", "not in", [41])]`]);

        await selectOperator(target, "=");
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "xpad");
        assert.verifySteps([`[("product_ids", "=", [41])]`]);

        await selectOperator(target, "!=");
        assert.strictEqual(getCurrentOperator(target), "!=");
        assert.strictEqual(getCurrentValue(target), "xpad");
        assert.verifySteps([`[("product_ids", "!=", [41])]`]);
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
        assert.strictEqual(getCurrentOperator(target), "contains");
        assert.containsNone(target, ".o-autocomplete--input");
        assert.containsOnce(target, `${SELECTORS.valueEditor} .o_input`);
        assert.strictEqual(getCurrentValue(target), "abc");
        assert.verifySteps([]);

        await editInput(target, `${SELECTORS.valueEditor} .o_input`, "def");
        assert.strictEqual(getCurrentOperator(target), "contains");
        assert.containsOnce(target, `${SELECTORS.valueEditor} .o_input`);
        assert.strictEqual(getCurrentValue(target), "def");
        assert.verifySteps([`[("product_ids", "ilike", "def")]`]);

        await selectOperator(target, "not ilike");
        assert.strictEqual(getCurrentOperator(target), "does not contain");
        assert.containsOnce(target, `${SELECTORS.valueEditor} .o_input`);
        assert.strictEqual(getCurrentValue(target), "def");
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
        assert.strictEqual(getCurrentOperator(target), "is not set");
        assert.containsNone(target, ".o_ds_value_cell");
        assert.verifySteps([]);

        await selectOperator(target, "set");
        assert.strictEqual(getCurrentOperator(target), "is set");
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
        assert.containsN(target, SELECTORS.condition, 2);
        assert.containsOnce(target, '.form-switch label:contains("Include archived")');

        await toggleArchive(target);
        assert.containsN(target, SELECTORS.condition, 2);
        assert.verifySteps([
            '["&", "&", ("foo", "=", "test"), ("bar", "=", True), ("active", "in", [True, False])]',
        ]);

        await click(target, ".dropdown-toggle");
        await click(target, ".dropdown-menu span:nth-child(2)");
        assert.containsN(target, SELECTORS.condition, 2);
        assert.verifySteps([
            '["&", "|", ("foo", "=", "test"), ("bar", "=", True), ("active", "in", [True, False])]',
        ]);

        await toggleArchive(target);
        assert.containsN(target, SELECTORS.condition, 2);
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
        assert.containsOnce(target, SELECTORS.condition);
        assert.containsOnce(target, '.form-switch label:contains("Include archived")');

        await toggleArchive(target);
        assert.containsOnce(target, SELECTORS.condition);
        assert.verifySteps(['["&", ("foo", "=", "test"), ("active", "in", [True, False])]']);

        await clickOnButtonDeleteNode(target);
        assert.containsNone(target, SELECTORS.condition);
        assert.verifySteps(['[("active", "in", [True, False])]']);

        await toggleArchive(target);
        assert.verifySteps(["[]"]);

        await toggleArchive(target);
        assert.containsNone(target, SELECTORS.condition);
        assert.verifySteps(['[("active", "in", [True, False])]']);

        await addNewRule(target);
        assert.containsOnce(target, SELECTORS.condition);
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
            assert.containsOnce(target, SELECTORS.condition);
            assert.containsNone(target, '.form-switch label:contains("Include archived")');
        }
    );

    QUnit.test("date/datetime edition: switch !=/is set", async (assert) => {
        await makeDomainSelector({
            isDebugMode: true,
            domain: `[("date", "!=", False)]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getCurrentOperator(target), "!=");
        assert.containsOnce(target, ".o_datetime_input");
        assert.strictEqual(getCurrentValue(target), "");

        await selectOperator(target, "set");
        assert.strictEqual(getCurrentOperator(target), "is set");
        assert.containsNone(target, ".o_datetime_input");
        assert.verifySteps([`[("date", "!=", False)]`]);

        await selectOperator(target, "!=");
        assert.strictEqual(getCurrentOperator(target), "!=");
        assert.containsOnce(target, ".o_datetime_input");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([`[("date", "!=", False)]`]);
    });

    QUnit.test("render false and true leaves", async (assert) => {
        await makeDomainSelector({ domain: `[(0, "=", 1), (1, "=", 1)]` });
        assert.deepEqual(getOperatorOptions(target), ["="]);
        assert.deepEqual(getValueOptions(target), ["1"]);
        assert.deepEqual(getOperatorOptions(target, -1), ["="]);
        assert.deepEqual(getValueOptions(target, -1), ["1"]);
    });

    QUnit.test("datetime domain in readonly mode (check localization)", async (assert) => {
        patchWithCleanup(localization, {
            dateTimeFormat: "MM.dd.yyyy HH:mm:ss",
        });
        patchTimeZone(120);
        await makeDomainSelector({
            domain: `["&", ("datetime", ">=", "2023-11-03 11:41:23"), ("datetime", "<=", "2023-11-13 09:45:11")]`,
            readonly: true,
        });
        assert.strictEqual(
            target.querySelector(".o_tree_editor_condition").textContent,
            `Date Timeis between11.03.2023 13:41:23 and 11.13.2023 11:45:11`
        );
    });

    QUnit.test("date domain in readonly mode (check localization)", async (assert) => {
        patchWithCleanup(localization, {
            dateFormat: `dd|MM|yyyy`,
        });
        patchTimeZone(120);
        await makeDomainSelector({
            domain: `["&", ("date", ">=", "2023-11-03"), ("date", "<=", "2023-11-13")]`,
            readonly: true,
        });
        assert.strictEqual(
            target.querySelector(".o_tree_editor_condition").textContent,
            `Dateis between03|11|2023 and 13|11|2023`
        );
    });

    QUnit.test("shorten descriptions of long lists", async (assert) => {
        const values = new Array(500).fill(42525245);
        await makeDomainSelector({
            domain: `[("id", "in", [${values}])]`,
            readonly: true,
        });
        assert.strictEqual(
            target.querySelector(".o_tree_editor_condition").textContent,
            `IDis in( ${values.slice(0, 20).join(" , ")} , ... )`
        );
    });

    QUnit.test("many2one: no domain in autocompletion", async (assert) => {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        serverData.models.partner.fields.product_id.domain = `[("display_name", "ilike", "xpa")]`;
        await makeDomainSelector({
            domain: `[("product_id", "=", False)]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([]);
        assert.containsNone(target, ".dropdown-menu");

        await editValue(target, "x");

        assert.containsOnce(target, ".dropdown-menu");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".dropdown-menu li")), [
            "xphone",
            "xpad",
        ]);
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "x");

        await click(target.querySelector(".dropdown-menu li"));
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "xphone");
        assert.verifySteps([`[("product_id", "=", 37)]`]);
        assert.containsNone(target, ".dropdown-menu");
    });

    QUnit.test("many2many: domain in autocompletion", async (assert) => {
        addProductIds();
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        serverData.models.partner.fields.product_ids.domain = `[("display_name", "ilike", "xpa")]`;
        await makeDomainSelector({
            domain: `[("product_ids", "=", [])]`,
            update(domain) {
                assert.step(domain);
            },
        });
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "");
        assert.verifySteps([]);
        assert.containsNone(target, ".dropdown-menu");

        await editValue(target, "x");

        assert.containsOnce(target, ".dropdown-menu");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".dropdown-menu li")), [
            "xpad",
        ]);
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "x");

        await click(target, ".dropdown-menu li");
        assert.strictEqual(getCurrentOperator(target), "=");
        assert.strictEqual(getCurrentValue(target), "xpad");
        assert.verifySteps([`[("product_ids", "=", [41])]`]);
        assert.containsNone(target, ".dropdown-menu");
    });
});
