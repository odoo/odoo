import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllAttributes, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame, mockTimeZone, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";

import {
    getPickerApplyButton,
    getPickerCell,
} from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    Partner,
    Product,
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
    getValueOptions,
    isNotSupportedOperator,
    isNotSupportedPath,
    isNotSupportedValue,
    openModelFieldSelectorPopover,
    selectOperator,
    selectValue,
    toggleArchive,
} from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineModels,
    fields,
    makeMockServer,
    models,
    mountWithCleanup,
    onRpc,
    patchDate,
} from "@web/../tests/web_test_helpers";
import { SELECTORS } from "./domain_selector_helpers";

import { DomainSelector } from "@web/core/domain_selector/domain_selector";

function addProductIds() {
    Partner._fields.product_ids = fields.Many2many({
        string: "Products",
        relation: "product",
        searchable: true,
    });
}

async function makeDomainSelector(params = {}) {
    const props = { ...params };

    class Parent extends Component {
        static components = { DomainSelector };
        static template = xml`<DomainSelector t-props="domainSelectorProps"/>`;
        static props = ["*"];
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
            await animationFrame();
        }
    }
    return mountWithCleanup(Parent, { props });
}

defineModels([Partner, Product]);

test("creating a domain from scratch", async () => {
    await makeDomainSelector({
        isDebugMode: true,
    });

    // As we gave an empty domain, there should be a visible button to add
    // the first domain part
    expect(SELECTORS.addNewRule).toHaveCount(1);

    // Clicking on that button should add a visible field selector in the
    // component so that the user can change the field chain
    await addNewRule();
    expect(".o_model_field_selector").toHaveCount(1);

    // Focusing the field selector input should open a field selector popover
    await openModelFieldSelectorPopover();
    expect(".o_model_field_selector_popover").toHaveCount(1, {
        message: "field selector popover should be visible",
    });
    // The field selector popover should contain the list of "partner"
    // fields. "Bar" should be among them. "Bar" result li will display the
    // name of the field and some debug info.
    expect(
        ".o_model_field_selector_popover .o_model_field_selector_popover_item_name:first"
    ).toHaveText("Bar\nbar (boolean)", {
        message: "field selector popover should contain the 'Bar' field",
    });

    // Clicking the "Bar" field should change the internal domain and this
    // should be displayed in the debug textarea
    await contains(
        ".o_model_field_selector_popover .o_model_field_selector_popover_item_name"
    ).click();
    expect(SELECTORS.debugArea).toHaveCount(1);
    expect(SELECTORS.debugArea).toHaveValue(`[("bar", "=", True)]`);

    // There should be a "+" button to add a domain part; clicking on it
    // should add the default "('id', '=', 1)" domain
    expect(SELECTORS.buttonAddNewRule).toHaveCount(1);
    await clickOnButtonAddNewRule();
    expect(SELECTORS.debugArea).toHaveValue(`["&", ("bar", "=", True), ("bar", "=", True)]`);

    // There should be two "Add branch" buttons to add a domain "branch"; clicking on
    // the first one, should add this group with defaults "('id', '=', 1)"
    // domains and the "|" operator
    expect(SELECTORS.buttonAddBranch).toHaveCount(2);
    await clickOnButtonAddBranch();
    expect(SELECTORS.debugArea).toHaveValue(
        `["&", "&", ("bar", "=", True), "|", ("id", "=", 1), ("id", "=", 1), ("bar", "=", True)]`
    );

    // There should be five buttons to remove domain part; clicking on
    // the two last ones, should leave a domain with only the "bar" and
    // "foo" fields, with the initial "&" operator
    expect(SELECTORS.buttonDeleteNode).toHaveCount(5);
    await clickOnButtonDeleteNode(-1);
    await clickOnButtonDeleteNode(-1);
    expect(SELECTORS.debugArea).toHaveValue(`["&", ("bar", "=", True), ("id", "=", 1)]`);
});

test("building a domain with a datetime", async () => {
    expect.assertions(4);

    await makeDomainSelector({
        domain: `[("datetime", "=", "2017-03-27 15:42:00")]`,
        isDebugMode: true,
        update(domain) {
            expect(domain).toBe(`[("datetime", "=", "2017-02-26 15:42:00")]`);
        },
    });

    // Check that there is a datepicker to choose the date
    expect(".o_datetime_input").toHaveCount(1, { message: "there should be a datepicker" });

    // The input field should display the date and time in the user's timezone
    expect(".o_datetime_input").toHaveValue("03/27/2017 16:42:00");

    // Change the date in the datepicker
    await contains(".o_datetime_input").click();
    await contains(getPickerCell("26").at(0)).click();
    await contains(getPickerApplyButton()).click();

    // The input field should display the date and time in the user's timezone
    expect(".o_datetime_input").toHaveValue("02/26/2017 16:42:00");
});

test("building a domain with an invalid path", async () => {
    await makeDomainSelector({
        domain: `[("fooooooo", "=", "abc")]`,
        update(domain) {
            expect(domain).toBe(`[("bar", "=", True)]`);
        },
    });

    expect(getCurrentPath()).toBe("fooooooo");
    expect(".o_model_field_selector_warning").toHaveCount(1);
    expect(".o_model_field_selector_warning").toHaveAttribute("title", "Invalid field chain");
    expect(getOperatorOptions()).toHaveLength(1);
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("abc");

    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item_name").click();
    expect(getCurrentPath()).toBe("Bar");
    expect(getCurrentOperator()).toBe("is");
    expect(getCurrentValue()).toBe("set");
});

test("building a domain with an invalid path (2)", async () => {
    await makeDomainSelector({
        domain: `[(bloup, "=", "abc")]`,
        update(domain) {
            expect(domain).toBe(`[("id", "=", 1)]`);
        },
    });

    expect(getCurrentPath()).toBe("bloup");
    expect(isNotSupportedPath()).toBe(true);
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("abc");

    await clearNotSupported();
    expect(getCurrentPath()).toBe("Id");
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("1");
});

test("building a domain with an invalid path (3)", async () => {
    Partner._fields.user_id = fields.Many2one({
        string: "User",
        relation: "users",
        searchable: true,
    });
    defineModels([class Users extends models.Model {}]);
    await makeDomainSelector({
        domain: `[(bloup, "=", "abc")]`,
        update(domain) {
            expect(domain).toBe(`[("user_id", "in", [])]`);
        },
    });

    expect(getCurrentPath()).toBe("bloup");
    expect(isNotSupportedPath()).toBe(true);
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("abc");

    await clearNotSupported();
    expect(getCurrentPath()).toBe("User");
    expect(getCurrentOperator()).toBe("is in");
    expect(getCurrentValue()).toBe("");
});

test("building a domain with an invalid operator", async () => {
    await makeDomainSelector({
        domain: `[("foo", "!!!!=!!!!", "abc")]`,
        update(domain) {
            expect(domain).toBe(`[("foo", "=", "abc")]`);
        },
    });

    expect(getCurrentPath()).toBe("Foo");
    expect(".o_model_field_selector_warning").toHaveCount(0);
    expect(getCurrentOperator()).toBe(`"!!!!=!!!!"`);
    expect(isNotSupportedOperator()).toBe(true);
    expect(getCurrentValue()).toBe("abc");

    await clearNotSupported();
    expect(getCurrentPath()).toBe("Foo");
    expect(".o_model_field_selector_warning").toHaveCount(0);
    expect(getOperatorOptions()).toHaveLength(8);
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("abc");
});

test("building a domain with an expression for value", async () => {
    patchDate("2023-04-20 17:00:00", 0);
    await makeDomainSelector({
        domain: `[("datetime", ">=", context_today())]`,
        update(domain) {
            expect(domain).toBe(`[("datetime", ">=", "2023-04-20 17:00:00")]`);
        },
    });

    expect(getCurrentValue()).toBe("context_today()");
    await clearNotSupported();
    expect(getCurrentValue()).toBe("04/20/2023 17:00:00");
});

test("building a domain with an expression in value", async () => {
    await makeDomainSelector({
        domain: `[("int", "=", id)]`,
        update(domain) {
            expect(domain).toBe(`[("int", "<", 1)]`);
        },
    });

    expect(getCurrentPath()).toBe("Int");
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("id");

    await selectOperator("<");

    expect(getCurrentPath()).toBe("Int");
    expect(getCurrentOperator()).toBe("<");
    expect(getCurrentValue()).toBe("1");
});

test("building a domain with a m2o without following the relation", async () => {
    await makeDomainSelector({
        domain: `[("product_id", "ilike", 1)]`,
        isDebugMode: true,
        update: (domain) => {
            expect.step(domain);
        },
    });
    expect([]).toVerifySteps();
    expect(isNotSupportedValue()).toBe(true);

    await clearNotSupported();
    expect([`[("product_id", "ilike", "")]`]).toVerifySteps();

    await contains(`${SELECTORS.valueEditor} input`).edit("pad");
    expect([`[("product_id", "ilike", "pad")]`]).toVerifySteps();
});

test("editing a domain with `parent` key", async () => {
    await makeDomainSelector({
        resModel: "product",
        domain: `[("name", "=", parent.foo)]`,
        isDebugMode: true,
    });

    expect.assertions(2);

    expect(getCurrentValue()).toBe("parent.foo");
    expect(isNotSupportedValue()).toBe(true);
});

test("edit a domain with the debug textarea", async () => {
    expect.assertions(5);

    let newDomain;
    await makeDomainSelector({
        domain: `[("product_id", "ilike", 1)]`,
        isDebugMode: true,
        update(domain, fromDebug) {
            expect(domain).toBe(newDomain);
            expect(fromDebug).toBe(true);
        },
    });

    expect(SELECTORS.condition).toHaveCount(1);

    newDomain = `[['product_id', 'ilike', 1],['id', '=', 0]]`;
    await contains(SELECTORS.debugArea).edit(newDomain, {
        message: "the domain should not have been formatted",
    });
    expect(SELECTORS.debugArea).toHaveValue(newDomain);
    expect(SELECTORS.condition).toHaveCount(2);
});

test("set [(1, '=', 1)] or [(0, '=', 1)] as domain with the debug textarea", async () => {
    expect.assertions(11);

    let newDomain;
    await makeDomainSelector({
        domain: `[("product_id", "ilike", 1)]`,
        isDebugMode: true,
        update(domain, fromDebug) {
            expect(domain).toBe(newDomain);
            expect(fromDebug).toBe(true);
        },
    });

    expect(SELECTORS.condition).toHaveCount(1);

    newDomain = `[(1, "=", 1)]`;
    await contains(SELECTORS.debugArea).edit(newDomain);
    expect(SELECTORS.debugArea).toHaveValue(newDomain, {
        message: "the domain should not have been formatted",
    });

    newDomain = `[(0, "=", 1)]`;
    await contains(SELECTORS.debugArea).edit(newDomain);
    expect(SELECTORS.debugArea).toHaveValue(newDomain, {
        message: "the domain should not have been formatted",
    });
    expect(SELECTORS.condition).toHaveCount(1);
    expect(getCurrentPath()).toBe("0");
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("1");
});

test("operator fallback (mode readonly)", async () => {
    await makeDomainSelector({
        domain: `[['foo', 'like', 'kikou']]`,
        readonly: true,
    });
    expect(getConditionText()).toBe(`Foo like kikou`);
});

test("cache fields_get", async () => {
    onRpc("fields_get", ({ method }) => expect.step(method));

    await makeDomainSelector({
        domain: "['&', ['foo', '=', 'kikou'], ['bar', '=', 'true']]",
    });
    expect(["fields_get"]).toVerifySteps();
});

test("selection field with operator change from 'is set' to '='", async () => {
    await makeDomainSelector({ domain: `[['state', '!=', False]]` });
    expect(getCurrentPath()).toBe("State");
    expect(getCurrentOperator()).toBe("is set");

    await selectOperator("=");
    expect(getCurrentPath()).toBe("State");
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe(`ABC`);
});

test("show correct operator", async () => {
    await makeDomainSelector({ domain: `[['state', 'in', ['abc']]]` });
    expect(getCurrentOperator()).toBe("is in");
});

test("multi selection", async () => {
    class Parent extends Component {
        static components = { DomainSelector };
        static template = xml`
            <DomainSelector
                resModel="'partner'"
                domain="domain"
                readonly="false"
                update.bind="update"
            />
        `;
        static props = ["*"];
        setup() {
            this.domain = `[("state", "in", ["a", "b", "c"])]`;
        }
        update(domain) {
            this.domain = domain;
            this.render();
        }
    }

    // Create the domain selector and its mock environment
    const comp = await mountWithCleanup(Parent);
    expect(comp.domain).toBe(`[("state", "in", ["a", "b", "c"])]`);
    expect(queryAllTexts(SELECTORS.tag)).toEqual(["a", "b", "c"]);
    expect(`${SELECTORS.valueEditor} select`).toHaveCount(1);

    await contains(`${SELECTORS.valueEditor} .o_tag .o_delete`).click();
    expect(comp.domain).toBe(`[("state", "in", ["b", "c"])]`);

    await selectValue("abc");
    expect(comp.domain).toBe(`[("state", "in", ["b", "c", "abc"])]`);
    const tags = queryAll(SELECTORS.tag);
    expect(tags[0]).toHaveClass("o_tag_color_2");
    expect(tags[1]).toHaveClass("o_tag_color_2");
    expect(tags[2]).toHaveClass("o_tag_color_0");
});

test("json field with operator change from 'equal' to 'ilike'", async () => {
    await makeDomainSelector({ domain: `[['json_field', '=', "hey"]]` });
    expect(getCurrentPath()).toBe(`Json Field`);
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe(`hey`);

    await selectOperator("ilike");
    expect(getCurrentOperator()).toBe("contains");
});

test("parse -1", async () => {
    class Parent extends Component {
        static components = { DomainSelector };
        static template = xml`
            <DomainSelector resModel="'partner'" domain="domain" readonly="false"/>
        `;
        static props = ["*"];
        setup() {
            this.domain = `[("id", "=", -1)]`;
        }
    }
    await mountWithCleanup(Parent);
    expect(getCurrentValue()).toBe("-1");
});

test("parse 3-1", async () => {
    class Parent extends Component {
        static components = { DomainSelector };
        static template = xml`
            <DomainSelector resModel="'partner'" domain="domain" readonly="false"/>
        `;
        static props = ["*"];
        setup() {
            this.domain = `[("id", "=", 3-1)]`;
        }
    }
    await mountWithCleanup(Parent);
    expect(getCurrentValue()).toBe("3 - 1");
});

test("domain not supported (mode readonly)", async () => {
    await mountWithCleanup(DomainSelector, {
        props: {
            resModel: "partner",
            domain: `[`,
            readonly: true,
            isDebugMode: false,
        },
    });
    expect(SELECTORS.resetButton).toHaveCount(0);
    expect(SELECTORS.debugArea).toHaveCount(0);
});

test("domain not supported (mode readonly + mode debug)", async () => {
    await mountWithCleanup(DomainSelector, {
        props: {
            resModel: "partner",
            domain: `[`,
            readonly: true,
            isDebugMode: true,
        },
    });
    expect(SELECTORS.resetButton).toHaveCount(0);
    expect(SELECTORS.debugArea).toHaveCount(1);
    expect(SELECTORS.debugArea).toHaveAttribute("readonly");
});

test("domain not supported (mode edit)", async () => {
    await mountWithCleanup(DomainSelector, {
        props: {
            resModel: "partner",
            domain: `[`,
            readonly: false,
            isDebugMode: false,
        },
    });
    expect(SELECTORS.resetButton).toHaveCount(1);
    expect(SELECTORS.debugArea).toHaveCount(0);
});

test("domain not supported (mode edit + mode debug)", async () => {
    await makeDomainSelector({
        domain: `[`,
        isDebugMode: true,
    });
    expect(SELECTORS.resetButton).toHaveCount(1);
    expect(SELECTORS.debugArea).toHaveCount(1);
    expect(SELECTORS.debugArea).not.toHaveAttribute("readonly");
});

test("reset domain", async () => {
    await makeDomainSelector({
        domain: `[`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(".o_domain_selector").toHaveText("This domain is not supported.\nReset domain");
    expect(SELECTORS.resetButton).toHaveCount(1);
    expect(SELECTORS.addNewRule).toHaveCount(0);

    await contains(SELECTORS.resetButton).click();
    expect(".o_domain_selector").toHaveText("Match all records\nNew Rule");
    expect(SELECTORS.resetButton).toHaveCount(0);
    expect(SELECTORS.addNewRule).toHaveCount(1);
    expect(["[]"]).toVerifySteps();
});

test("default condition depends on available fields", async () => {
    Partner._fields.user_id = fields.Many2one({
        string: "User",
        relation: "users",
        searchable: true,
    });
    defineModels([class Users extends models.Model {}]);
    await makeDomainSelector({
        domain: `[]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(".o_domain_selector").toHaveText("Match all records\nNew Rule");
    await addNewRule();
    expect(['[("user_id", "in", [])]']).toVerifySteps();
});

test("debug input in model field selector popover", async () => {
    class Parent extends Component {
        static components = { DomainSelector };
        static template = xml`
            <DomainSelector
                resModel="'partner'"
                domain="domain"
                readonly="false"
                isDebugMode="true"
                update.bind="update"
            />
        `;
        static props = ["*"];
        setup() {
            this.domain = `[("id", "=", 1)]`;
        }
        update(domain) {
            expect.step(domain);
            this.domain = domain;
            this.render();
        }
    }
    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_debug").edit("a", { confirm: "tab" });
    await contains(".o_model_field_selector_popover_close").click();
    expect([`[("a", "=", 1)]`]).toVerifySteps();
    expect(getCurrentPath()).toBe("a");
    expect(".o_model_field_selector_warning").toHaveCount(1);
    expect(getOperatorOptions()).toHaveLength(1);
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("1");
    expect(SELECTORS.debugArea).toHaveValue(`[("a", "=", 1)]`);
});

test("between operator", async () => {
    mockTimeZone(0);
    await makeDomainSelector({
        domain: `["&", ("datetime", ">=", "2023-01-01 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00")]`,
        isDebugMode: true,
        update(domain) {
            expect.step(domain);
        },
    });

    expect(SELECTORS.condition).toHaveCount(1);
    expect(getCurrentOperator()).toBe("is between");
    expect(".o_datetime_input").toHaveCount(2);

    await contains(".o_datetime_input:first").edit("2023-01-02 00:00:00");
    expect([
        `["&", ("datetime", ">=", "2023-01-02 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00")]`,
    ]).toVerifySteps();

    await contains(".o_datetime_input:eq(1)").edit("2023-01-08 00:00:00");
    expect([
        `["&", ("datetime", ">=", "2023-01-02 00:00:00"), ("datetime", "<=", "2023-01-08 00:00:00")]`,
    ]).toVerifySteps();
});

test("between operator (2)", async () => {
    mockTimeZone(0);
    await makeDomainSelector({
        domain: `["&", "&", ("foo", "=", "abc"), ("datetime", ">=", "2023-01-01 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00")]`,
    });
    expect(SELECTORS.condition).toHaveCount(2);
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentOperator(1)).toBe("is between");
    expect(".o_datetime_input").toHaveCount(2);
});

test("between operator (3)", async () => {
    mockTimeZone(0);
    await makeDomainSelector({
        domain: `["&", "&", ("datetime", ">=", "2023-01-01 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00"), ("foo", "=", "abc")]`,
    });
    expect(SELECTORS.condition).toHaveCount(2);
    expect(getCurrentOperator()).toBe("is between");
    expect(getCurrentOperator(1)).toBe("=");
    expect(".o_datetime_input").toHaveCount(2);
});

test("between operator (4)", async () => {
    mockTimeZone(0);
    await makeDomainSelector({
        domain: `["&", ("datetime", ">=", "2023-01-01 00:00:00"), "&", ("datetime", "<=", "2023-01-10 00:00:00"), ("foo", "=", "abc")]`,
    });
    expect(SELECTORS.condition).toHaveCount(2);
    expect(getCurrentOperator()).toBe("is between");
    expect(getCurrentOperator(1)).toBe("=");
    expect(".o_datetime_input").toHaveCount(2);
});

test("between operator (5)", async () => {
    mockTimeZone(0);
    await makeDomainSelector({
        domain: `["|", "&", ("create_date", ">=", "2023-04-01 00:00:00"), ("create_date", "<=", "2023-04-30 23:59:59"), (0, "=", 1)]`,
        readonly: true,
    });
    expect(".o_domain_selector").toHaveText(
        `Match\nany\nof the following rules:\nCreated on\nis between\n04/01/2023 00:00:00\nand\n04/30/2023 23:59:59\n0\n=\n1`
    );
});

test("expressions in between operator", async () => {
    patchDate("2023-01-01 00:00:00", 0);
    await makeDomainSelector({
        domain: `["&", ("datetime", ">=", context_today()), ("datetime", "<=", "2023-01-10 00:00:00")]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(SELECTORS.condition).toHaveCount(1);
    expect(getCurrentOperator()).toBe("is between");
    expect(SELECTORS.valueEditor).toHaveCount(1);
    expect(SELECTORS.valueEditor).toHaveCount(1);
    expect(SELECTORS.valueEditor + " " + SELECTORS.editor).toHaveCount(2);
    expect(SELECTORS.clearNotSupported).toHaveCount(1);
    expect(`${SELECTORS.editor} .o_datetime_input`).toHaveCount(1);

    await clearNotSupported();
    expect(SELECTORS.valueEditor).toHaveCount(1);
    expect(`${SELECTORS.editor} .o_datetime_input`).toHaveCount(2);
    expect([
        `["&", ("datetime", ">=", "2023-01-01 00:00:00"), ("datetime", "<=", "2023-01-10 00:00:00")]`,
    ]).toVerifySteps();
});

test("support of connector '!' (mode readonly)", async () => {
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
        static components = { DomainSelector };
        static template = xml`<DomainSelector resModel="'partner'" domain="state.domain"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ domain: `[]` });
        }
    }

    const parent = await mountWithCleanup(Parent);

    for (const { domain, result } of toTest) {
        parent.state.domain = domain;
        await animationFrame();
        expect(".o_domain_selector").toHaveText(result);
    }
});

test("support of connector '!' (debug mode)", async () => {
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
        static components = { DomainSelector };
        static template = xml`<DomainSelector resModel="'partner'" isDebugMode="true" domain="state.domain"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ domain: `[]` });
        }
    }

    const parent = await mountWithCleanup(Parent);

    for (const { domain, result } of toTest) {
        parent.state.domain = domain;
        await animationFrame();
        expect(".o_domain_selector").toHaveText(result);
    }
});

test("support properties", async () => {
    expect.assertions(25);
    patchDate("2023-10-05 15:00:00", 0);

    Partner._fields.properties = fields.Properties({
        string: "Properties",
        definition_record: "product_id",
        definition_record_field: "definitions",
        searchable: true,
    });
    Product._fields.definitions = fields.PropertiesDefinition({
        string: "Definitions",
    });
    Product._records[0].definitions = [
        { name: "xphone_prop_1", string: "Boolean", type: "boolean" },
        { name: "xphone_prop_2", string: "Selection", type: "selection", selection: [] },
        { name: "xphone_prop_3", string: "Char", type: "char" },
        { name: "xphone_prop_4", string: "Integer", type: "integer" },
        { name: "xphone_prop_5", string: "Date", type: "date" },
        { name: "xphone_prop_6", string: "Tags", type: "tags" },
        { name: "xphone_prop_7", string: "M2M", type: "many2many", comodel: "partner" },
    ];
    Product._records[1].definitions = [
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
                update.bind="update"
            />
        `;
        static components = { DomainSelector };
        static props = ["*"];
        setup() {
            this.domain = expectedDomain;
        }
        update(domain) {
            expect(domain).toBe(expectedDomain);
            this.domain = domain;
            this.render();
        }
    }

    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();
    await contains(
        ".o_model_field_selector_popover_item[data-name='properties'] .o_model_field_selector_popover_relation_icon"
    ).click();
    expect(getCurrentPath()).toBe("Properties");
    expectedDomain = `[("properties.xpad_prop_1", "=", False)]`;
    await contains(".o_model_field_selector_popover_item[data-name='xpad_prop_1'] button").click();
    expect(getCurrentPath()).toBe("Properties > M2O");
    expect(getOperatorOptions()).toEqual(["=", "!=", "is set", "is not set"]);

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
        await openModelFieldSelectorPopover();
        expectedDomain = domain;
        await contains(`.o_model_field_selector_popover_item[data-name='${name}'] button`).click();
        const { string } = Product._records[0].definitions.find((def) => def.name === name);
        expect(getCurrentPath()).toBe(`Properties > ${string}`);
        expect(getOperatorOptions()).toEqual(options);
    }
});

test("support properties (mode readonly)", async () => {
    Partner._fields.properties = fields.Properties({
        string: "Properties",
        definition_record: "product_id",
        definition_record_field: "definitions",
        searchable: true,
    });
    Product._fields.definitions = fields.PropertiesDefinition({
        string: "Definitions",
    });
    Product._records[0].definitions = [
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
    Product._records[1].definitions = [
        { name: "xpad_prop_1", string: "M2O", type: "many2one", comodel: "product" },
    ];

    await makeMockServer({
        lang_parameters: {
            date_format: "%d|%m|%Y",
        },
    });
    const toTest = [
        {
            domain: `[("properties.xphone_prop_1", "=", False)]`,
            result: "PropertiesBoolean is not set",
        },
        {
            domain: `[("properties.xphone_prop_2", "=", "abc")]`,
            result: "PropertiesSelection = ABC",
        },
        { domain: `[("properties.xphone_prop_3", "=", "def")]`, result: "PropertiesChar = def" },
        { domain: `[("properties.xphone_prop_4", "=", 1)]`, result: "PropertiesInteger = 1" },
        {
            domain: `[("properties.xphone_prop_5", "=", "2023-10-05")]`,
            result: "PropertiesDate = 05|10|2023",
        },
        { domain: `[("properties.xphone_prop_6", "in", "g")]`, result: "PropertiesTags is in g" },
        {
            domain: `[("properties.xphone_prop_7", "in", [37])]`,
            result: "PropertiesM2M is in ( xphone )",
        },
        { domain: `[("properties.xpad_prop_1", "=", 41)]`, result: "PropertiesM2O = xpad" },
    ];

    class Parent extends Component {
        static components = { DomainSelector };
        static template = xml`<DomainSelector resModel="'partner'" domain="state.domain"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ domain: `[]` });
        }
    }

    const parent = await mountWithCleanup(Parent);

    for (const { domain, result } of toTest) {
        parent.state.domain = domain;
        await animationFrame();
        expect(getConditionText()).toBe(result);
    }
});

test("no button 'New Rule' (mode readonly)", async () => {
    await makeDomainSelector({
        readonly: true,
        domain: `[("bar", "=", True)]`,
    });
    expect(SELECTORS.condition).toHaveCount(1);
    expect("a[role=button]").toHaveCount(0);
});

test("button 'New Rule' (edit mode)", async () => {
    await makeDomainSelector();
    expect(SELECTORS.condition).toHaveCount(0);
    expect(SELECTORS.addNewRule).toHaveCount(1);

    await addNewRule();
    expect(SELECTORS.condition).toHaveCount(1);
    expect(SELECTORS.addNewRule).toHaveCount(1);

    await addNewRule();
    expect(SELECTORS.condition).toHaveCount(2);
    expect(SELECTORS.addNewRule).toHaveCount(1);
});

test("updating path should also update operator if invalid", async () => {
    await makeDomainSelector({
        domain: `[("id", "<", 0)]`,
        update: (domain) => {
            expect(domain).toBe(`[("foo", "=", "")]`);
        },
    });

    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item[data-name=foo] button").click();
});

test("treat false and true like False and True", async () => {
    const parent = await makeDomainSelector({
        resModel: "partner",
        domain: `[("bar","=",false)]`,
        readonly: true,
    });
    expect(getConditionText()).toBe(`Bar is not set`);
    await parent.set(`[("bar","=",true)]`);
    expect(getConditionText()).toBe(`Bar is set`);
});

test("Edit the value for field char and an operator in", async () => {
    const parent = await makeDomainSelector({
        resModel: "partner",
        domain: `[("foo", "in", ["a", "b", uid])]`,
        update: (domain) => {
            expect.step(domain);
        },
        isDebugMode: true,
    });
    expect(queryAllTexts(SELECTORS.tag)).toEqual([`"a"`, `"b"`, `uid`]);
    expect(queryAllAttributes(SELECTORS.tag, "data-color")).toEqual(["0", "0", "2"]);

    await editValue("c");
    expect(queryAllTexts(SELECTORS.tag)).toEqual([`"a"`, `"b"`, `uid`, `"c"`]);
    expect([`[("foo", "in", ["a", "b", uid, "c"])]`]).toVerifySteps();

    await contains(".o_tag .o_delete:eq(2)").click();
    expect(queryAllTexts(SELECTORS.tag)).toEqual([`a`, `b`, `c`]);
    expect([`[("foo", "in", ["a", "b", "c"])]`]).toVerifySteps();

    await parent.set(`[("foo", "in", ["a"])]`);
    expect(queryAllTexts(SELECTORS.tag)).toEqual([`a`]);

    await editValue("b");
    expect(queryAllTexts(SELECTORS.tag)).toEqual([`a`, `b`]);
    expect([`[("foo", "in", ["a", "b"])]`]).toVerifySteps();
});

test("display of an unknown operator (readonly)", async () => {
    const parent = await makeDomainSelector({
        resModel: "partner",
        domain: `[("foo", "hop", "a")]`,
        readonly: true,
    });
    expect(getConditionText()).toBe(`Foo "hop" a`);

    await parent.set(`[("foo", hop, "a")]`);
    expect(getConditionText()).toBe(`Foo hop a`);
});

test("display of an unknown operator (edit)", async () => {
    const parent = await makeDomainSelector({
        resModel: "partner",
        domain: `[("foo", "hop", "a")]`,
    });
    expect(getCurrentOperator()).toBe(`"hop"`);

    await parent.set(`[("foo", hop, "a")]`);
    expect(getCurrentOperator()).toBe(`hop`);
});

test("display of negation of an unknown operator (readonly)", async () => {
    const parent = await makeDomainSelector({
        resModel: "partner",
        domain: `["!", ("foo", "hop", "a")]`,
        readonly: true,
    });
    expect(getConditionText()).toBe(`Foo not "hop" a`);

    await parent.set(`["!", ("foo", hop, "a")]`);
    expect(getConditionText()).toBe(`Foo not hop a`);
});

test("display of an operator without negation defined (readonly)", async () => {
    await makeDomainSelector({
        resModel: "partner",
        domain: `["!", ("foo", "=?", "a")]`,
        readonly: true,
    });
    expect(getConditionText()).toBe("Foo not =? a");
});

test("display of an operator without negation defined (edit)", async () => {
    await makeDomainSelector({
        resModel: "partner",
        domain: `["!", ("foo", "=?", "a")]`,
    });
    expect(getCurrentOperator()).toBe("not =?");
});

test("display of an operator without negation defined (edit) 2", async () => {
    await makeDomainSelector({
        resModel: "partner",
        domain: `["!", ("expr", "parent_of", "a")]`,
    });
    expect(getCurrentOperator()).toBe("not parent of");
});

test("display of a contextual value (readonly)", async () => {
    await makeDomainSelector({
        domain: `[("foo", "=", uid)]`,
        readonly: true,
    });
    expect(getConditionText()).toBe("Foo = uid");
});

test("boolean field (readonly)", async () => {
    const parent = await makeDomainSelector({
        readonly: true,
        domain: `[]`,
    });
    const toTest = [
        { domain: `[("bar", "=", True)]`, text: "Bar is set" },
        { domain: `[("bar", "=", False)]`, text: "Bar is not set" },
        { domain: `[("bar", "!=", True)]`, text: "Bar is not set" },
        { domain: `[("bar", "!=", False)]`, text: "Bar is not not set" },
    ];
    for (const { domain, text } of toTest) {
        await parent.set(domain);
        expect(getConditionText()).toBe(text);
    }
});

test("integer field (readonly)", async () => {
    const parent = await makeDomainSelector({
        readonly: true,
        domain: `[]`,
    });
    const toTest = [
        { domain: `[("int", "=", True)]`, text: `Int = true` },
        { domain: `[("int", "=", False)]`, text: `Int is not set` },
        { domain: `[("int", "!=", True)]`, text: `Int != true` },
        { domain: `[("int", "!=", False)]`, text: `Int is set` },
        { domain: `[("int", "=", 1)]`, text: `Int = 1` },
        { domain: `[("int", "!=", 1)]`, text: `Int != 1` },
        { domain: `[("int", "<", 1)]`, text: `Int < 1` },
        { domain: `[("int", "<=", 1)]`, text: `Int <= 1` },
        { domain: `[("int", ">", 1)]`, text: `Int > 1` },
        { domain: `[("int", ">=", 1)]`, text: `Int >= 1` },
        {
            domain: `["&", ("int", ">=", 1),("int","<=", 2)]`,
            text: `Int is between 1 and 2`,
        },
    ];
    for (const { domain, text } of toTest) {
        await parent.set(domain);
        expect(getConditionText()).toBe(text);
    }
});

test("date field (readonly)", async () => {
    makeMockServer({
        lang_parameters: {
            date_format: "%d|%m|%Y",
        },
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
        expect(getConditionText()).toBe(text);
    }
});

test("char field (readonly)", async () => {
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
        expect(getConditionText()).toBe(text);
    }
});

test("selection field (readonly)", async () => {
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
        expect(getConditionText()).toBe(text);
    }
});

test("selection property (readonly)", async () => {
    Partner._fields.properties = fields.Properties({
        string: "Properties",
        definition_record: "product_id",
        definition_record_field: "definitions",
        searchable: true,
    });
    Product._fields.definitions = fields.PropertiesDefinition({
        string: "Definitions",
    });
    Product._records[0].definitions = [
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
            domain: `[("properties.selection_prop", "=", false)]`,
            text: `PropertiesSelection is not set`,
        },
        {
            domain: `[("properties.selection_prop", "!=", false)]`,
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
        expect(getConditionText()).toBe(text);
    }
});

test("many2one field (readonly)", async () => {
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
            domain: `[("product_id", "=", false)]`,
            text: "Product = false",
        },
        {
            domain: `[("product_id", "!=", false)]`,
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
        expect(getConditionText()).toBe(text);
    }
});

test("many2one field operators (edit)", async () => {
    await makeDomainSelector({
        domain: `[("product_id", "=", false)]`,
    });
    expect(getOperatorOptions()).toEqual([
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

test("many2one field: operator switch (edit)", async () => {
    await makeDomainSelector({
        domain: `[("product_id", "=", False)]`,
        update(domain) {
            expect.step(domain);
        },
    });
    await selectOperator("in");
    expect(queryAllTexts(SELECTORS.tag)).toEqual([]);
    expect(getCurrentValue()).toBe("");
    expect([`[("product_id", "in", [])]`]).toVerifySteps();

    await selectOperator("=");
    expect(getCurrentValue()).toBe("");
    expect([`[("product_id", "=", False)]`]).toVerifySteps();

    await selectOperator("not in");
    expect(queryAllTexts(SELECTORS.tag)).toEqual([]);
    expect(getCurrentValue()).toBe("");
    expect([`[("product_id", "not in", [])]`]).toVerifySteps();

    await selectOperator("ilike");
    expect(getCurrentValue()).toBe("");
    expect([`[("product_id", "ilike", "")]`]).toVerifySteps();

    await selectOperator("!=");
    expect(getCurrentValue()).toBe("");
    expect([`[("product_id", "!=", False)]`]).toVerifySteps();

    await selectOperator("not ilike");
    expect(getCurrentValue()).toBe("");
    expect([`[("product_id", "not ilike", "")]`]).toVerifySteps();
});

test("many2one field and operator =/!= (edit)", async () => {
    await makeDomainSelector({
        domain: `[("product_id", "=", False)]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("");
    expect([]).toVerifySteps();
    expect(".dropdown-menu").toHaveCount(0);

    await editValue("xph", { confirm: false });
    await runAllTimers();
    expect(".dropdown-menu").toHaveCount(1);
    expect(queryAllTexts(".dropdown-menu li")).toEqual(["xphone"]);
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("xph");

    await contains(".dropdown-menu li").click();
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("xphone");
    expect([`[("product_id", "=", 37)]`]).toVerifySteps();
    expect(".dropdown-menu").toHaveCount(0);

    await editValue("", { confirm: false });
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("");
    await contains(".o_domain_selector").click();
    expect([`[("product_id", "=", False)]`]).toVerifySteps();

    await selectOperator("!=");
    expect(getCurrentOperator()).toBe("!=");
    expect(getCurrentValue()).toBe("");
    expect([`[("product_id", "!=", False)]`]).toVerifySteps();

    await editValue("xpa", { confirm: false });
    await runAllTimers();
    await contains(".dropdown-menu li").click();
    expect(getCurrentOperator()).toBe("!=");
    expect(getCurrentValue()).toBe("xpad");
    expect([`[("product_id", "!=", 41)]`]).toVerifySteps();
});

test("many2one field on record with falsy display_name", async () => {
    Product._records[0].name = false;
    await makeDomainSelector({
        domain: `[("product_id", "=", False)]`,
    });
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("");
    expect(".dropdown-menu").toHaveCount(0);

    await contains(".o-autocomplete--input").click();

    expect("a.dropdown-item:first").toHaveText("Unnamed", {
        message: "should have a Unnamed as fallback of many2one display_name",
    });
});

test("many2one field and operator in/not in (edit)", async () => {
    await makeDomainSelector({
        domain: `[("product_id", "in", [37])]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(getCurrentOperator()).toBe("is in");
    expect(getCurrentValue()).toBe("xphone");
    expect([]).toVerifySteps();
    expect(".dropdown-menu").toHaveCount(0);
    await contains(SELECTORS.valueEditor + " input").fill("x", { confirm: false });
    await runAllTimers();
    expect(".dropdown-menu").toHaveCount(1);
    expect(queryAllTexts(".dropdown-menu li")).toEqual(["xpad"]);

    await contains(".dropdown-menu li").click();
    expect([`[("product_id", "in", [37, 41])]`]).toVerifySteps();
    expect(getCurrentValue()).toBe("xphone xpad");

    await selectOperator("not in");
    expect(getCurrentOperator()).toBe("is not in");
    expect(getCurrentValue()).toBe("xphone xpad");
    expect([`[("product_id", "not in", [37, 41])]`]).toVerifySteps();

    await contains(".o_tag .o_delete").click();
    expect(getCurrentOperator()).toBe("is not in");
    expect(getCurrentValue()).toBe("xpad");
    expect([`[("product_id", "not in", [41])]`]).toVerifySteps();
});

test("many2one field and operator ilike/not ilike (edit)", async () => {
    await makeDomainSelector({
        domain: `[("product_id", "ilike", "abc")]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(getCurrentOperator()).toBe("contains");
    expect(".o-autocomplete--input").toHaveCount(0);
    expect(`${SELECTORS.valueEditor} .o_input`).toHaveCount(1);
    expect(getCurrentValue()).toBe("abc");
    expect([]).toVerifySteps();

    await contains(`${SELECTORS.valueEditor} .o_input`).edit("def");
    expect(getCurrentOperator()).toBe("contains");
    expect(`${SELECTORS.valueEditor} .o_input`).toHaveCount(1);
    expect(getCurrentValue()).toBe("def");
    expect([`[("product_id", "ilike", "def")]`]).toVerifySteps();

    await selectOperator("not ilike");
    expect(getCurrentOperator()).toBe("does not contain");
    expect(`${SELECTORS.valueEditor} .o_input`).toHaveCount(1);
    expect(getCurrentValue()).toBe("def");
    expect([`[("product_id", "not ilike", "def")]`]).toVerifySteps();
});

test("many2many field and operator set/not set (edit)", async () => {
    await makeDomainSelector({
        domain: `[("product_id", "=", False)]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("");
    expect([]).toVerifySteps();

    await selectOperator("not_set");

    expect(getCurrentOperator()).toBe("is not set");
    expect(".o_ds_value_cell").toHaveCount(0);
    expect([`[("product_id", "=", False)]`]).toVerifySteps();

    await selectOperator("set");
    expect(getCurrentOperator()).toBe("is set");
    expect(".o_ds_value_cell").toHaveCount(0);
    expect([`[("product_id", "!=", False)]`]).toVerifySteps();

    await selectOperator("!=");
    expect(getCurrentOperator()).toBe("!=");
    expect(getCurrentValue()).toBe("");
    expect([`[("product_id", "!=", False)]`]).toVerifySteps();
});

test("many2many field: clone a set/not set condition", async () => {
    await makeDomainSelector({
        domain: `[("product_id", "=", False)]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("");
    expect([]).toVerifySteps();

    await selectOperator("not_set");
    expect(getCurrentOperator()).toBe("is not set");
    expect(".o_ds_value_cell").toHaveCount(0);
    expect([`[("product_id", "=", False)]`]).toVerifySteps();
    expect(SELECTORS.condition).toHaveCount(1);

    await clickOnButtonAddNewRule();
    expect(SELECTORS.condition).toHaveCount(2);
    expect(getCurrentOperator()).toBe("is not set");
    expect(getCurrentOperator(1)).toBe("is not set");
    expect([`["&", ("product_id", "=", False), ("product_id", "=", False)]`]).toVerifySteps();
});

test("x2many field operators (edit)", async () => {
    addProductIds();
    await makeDomainSelector({
        domain: `[("product_ids", "=", false)]`,
    });
    expect(getOperatorOptions()).toEqual([
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

test("x2many field: operator switch (edit)", async () => {
    addProductIds();
    await makeDomainSelector({
        domain: `[("product_ids", "=", false)]`,
        update(domain) {
            expect.step(domain);
        },
    });
    await selectOperator("in");
    expect(queryAllTexts(SELECTORS.tag)).toEqual([]);
    expect(getCurrentValue()).toBe("");
    expect([`[("product_ids", "in", [])]`]).toVerifySteps();

    await selectOperator("=");
    expect(queryAllTexts(SELECTORS.tag)).toEqual([]);
    expect(getCurrentValue()).toBe("");
    expect([`[("product_ids", "=", [])]`]).toVerifySteps();

    await selectOperator("not in");
    expect(queryAllTexts(SELECTORS.tag)).toEqual([]);
    expect(getCurrentValue()).toBe("");
    expect([`[("product_ids", "not in", [])]`]).toVerifySteps();

    await selectOperator("ilike");
    expect(getCurrentValue()).toBe("");
    expect([`[("product_ids", "ilike", "")]`]).toVerifySteps();

    await selectOperator("not_set");
    expect(".o_ds_value_cell").toHaveCount(0);
    expect([`[("product_ids", "=", False)]`]).toVerifySteps();

    await selectOperator("!=");
    expect(queryAllTexts(SELECTORS.tag)).toEqual([]);
    expect(getCurrentValue()).toBe("");
    expect([`[("product_ids", "!=", [])]`]).toVerifySteps();

    await selectOperator("not ilike");
    expect(getCurrentValue()).toBe("");
    expect([`[("product_ids", "not ilike", "")]`]).toVerifySteps();

    await selectOperator("set");
    expect(".o_ds_value_cell").toHaveCount(0);
    expect([`[("product_ids", "!=", False)]`]).toVerifySteps();
});

test("many2many field: operator =/!=/in/not in (edit)", async () => {
    addProductIds();
    await makeDomainSelector({
        domain: `[("product_ids", "in", [37])]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(getCurrentOperator()).toBe("is in");
    expect(getCurrentValue()).toBe("xphone");
    expect([]).toVerifySteps();
    expect(".dropdown-menu").toHaveCount(0);

    await contains(SELECTORS.valueEditor + " input").fill("x", { confirm: false });
    await runAllTimers();
    expect(".dropdown-menu").toHaveCount(1);
    expect(queryAllTexts(".dropdown-menu li")).toEqual(["xpad"]);

    await contains(".dropdown-menu li").click();
    expect([`[("product_ids", "in", [37, 41])]`]).toVerifySteps();
    expect(getCurrentValue()).toBe("xphone xpad");

    await selectOperator("not in");
    expect(getCurrentOperator()).toBe("is not in");
    expect(getCurrentValue()).toBe("xphone xpad");
    expect([`[("product_ids", "not in", [37, 41])]`]).toVerifySteps();

    await contains(".o_tag .o_delete").click();
    expect(getCurrentOperator()).toBe("is not in");
    expect(getCurrentValue()).toBe("xpad");
    expect([`[("product_ids", "not in", [41])]`]).toVerifySteps();

    await selectOperator("=");
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("xpad");
    expect([`[("product_ids", "=", [41])]`]).toVerifySteps();

    await selectOperator("!=");
    expect(getCurrentOperator()).toBe("!=");
    expect(getCurrentValue()).toBe("xpad");
    expect([`[("product_ids", "!=", [41])]`]).toVerifySteps();
});

test("many2many field: operator ilike/not ilike (edit)", async () => {
    addProductIds();
    await makeDomainSelector({
        domain: `[("product_ids", "ilike", "abc")]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(getCurrentOperator()).toBe("contains");
    expect(".o-autocomplete--input").toHaveCount(0);
    expect(`${SELECTORS.valueEditor} .o_input`).toHaveCount(1);
    expect(getCurrentValue()).toBe("abc");
    expect([]).toVerifySteps();

    await contains(`${SELECTORS.valueEditor} .o_input`).edit("def");
    expect(getCurrentOperator()).toBe("contains");
    expect(`${SELECTORS.valueEditor} .o_input`).toHaveCount(1);
    expect(getCurrentValue()).toBe("def");
    expect([`[("product_ids", "ilike", "def")]`]).toVerifySteps();

    await selectOperator("not ilike");
    expect(getCurrentOperator()).toBe("does not contain");
    expect(`${SELECTORS.valueEditor} .o_input`).toHaveCount(1);
    expect(getCurrentValue()).toBe("def");
    expect([`[("product_ids", "not ilike", "def")]`]).toVerifySteps();
});

test("many2many field: operator set/not set (edit)", async () => {
    addProductIds();
    await makeDomainSelector({
        domain: `[("product_ids", "=", False)]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(getCurrentOperator()).toBe("is not set");
    expect(".o_ds_value_cell").toHaveCount(0);
    expect([]).toVerifySteps();

    await selectOperator("set");
    expect(getCurrentOperator()).toBe("is set");
    expect(".o_ds_value_cell").toHaveCount(0);
    expect([`[("product_ids", "!=", False)]`]).toVerifySteps();
});

test("Include archived button basic use", async () => {
    Partner._fields.active = fields.Boolean({
        string: "Active",
        searchable: true,
    });
    await makeDomainSelector({
        isDebugMode: true,
        domain: `["&", ("foo", "=", "test"), ("bar", "=", True)]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(SELECTORS.condition).toHaveCount(2);
    expect('.form-switch label:contains("Include archived")').toHaveCount(1);

    await toggleArchive();
    expect(SELECTORS.condition).toHaveCount(2);
    expect([
        '["&", "&", ("foo", "=", "test"), ("bar", "=", True), ("active", "in", [True, False])]',
    ]).toVerifySteps();

    await contains(".dropdown-toggle").click();
    await contains(".dropdown-menu span:nth-child(2)").click();
    expect(SELECTORS.condition).toHaveCount(2);
    expect([
        '["&", "|", ("foo", "=", "test"), ("bar", "=", True), ("active", "in", [True, False])]',
    ]).toVerifySteps();

    await toggleArchive();
    expect(SELECTORS.condition).toHaveCount(2);
    expect(['["|", ("foo", "=", "test"), ("bar", "=", True)]']).toVerifySteps();
});

test("Include archived on empty tree", async () => {
    Partner._fields.active = fields.Boolean({
        string: "Active",
        searchable: true,
    });
    await makeDomainSelector({
        isDebugMode: true,
        domain: `[("foo", "=", "test")]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(SELECTORS.condition).toHaveCount(1);
    expect('.form-switch label:contains("Include archived")').toHaveCount(1);

    await toggleArchive();
    expect(SELECTORS.condition).toHaveCount(1);
    expect(['["&", ("foo", "=", "test"), ("active", "in", [True, False])]']).toVerifySteps();

    await clickOnButtonDeleteNode();
    expect(SELECTORS.condition).toHaveCount(0);
    expect(['[("active", "in", [True, False])]']).toVerifySteps();

    await toggleArchive();
    expect(["[]"]).toVerifySteps();

    await toggleArchive();
    expect(SELECTORS.condition).toHaveCount(0);
    expect(['[("active", "in", [True, False])]']).toVerifySteps();

    await addNewRule();
    expect(SELECTORS.condition).toHaveCount(1);
    expect(['["&", ("id", "=", 1), ("active", "in", [True, False])]']).toVerifySteps();
});

test("Include archived not shown when model doesn't have the active field", async () => {
    await makeDomainSelector({
        isDebugMode: true,
        domain: `[("foo", "=", "test")]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(SELECTORS.condition).toHaveCount(1);
    expect('.form-switch label:contains("Include archived")').toHaveCount(0);
});

test("date/datetime edition: switch !=/is set", async () => {
    await makeDomainSelector({
        isDebugMode: true,
        domain: `[("date", "!=", False)]`,
        update(domain) {
            expect.step(domain);
        },
    });
    expect(getCurrentOperator()).toBe("!=");
    expect(".o_datetime_input").toHaveCount(1);
    expect(getCurrentValue()).toBe("");

    await selectOperator("set");
    expect(getCurrentOperator()).toBe("is set");
    expect(".o_datetime_input").toHaveCount(0);
    expect([`[("date", "!=", False)]`]).toVerifySteps();

    await selectOperator("!=");
    expect(getCurrentOperator()).toBe("!=");
    expect(".o_datetime_input").toHaveCount(1);
    expect(getCurrentValue()).toBe("");
    expect([`[("date", "!=", False)]`]).toVerifySteps();
});

test("render false and true leaves", async () => {
    await makeDomainSelector({ domain: `[(0, "=", 1), (1, "=", 1)]` });
    expect(getOperatorOptions()).toEqual(["="]);
    expect(getValueOptions()).toEqual(["1"]);
    expect(getOperatorOptions(-1)).toEqual(["="]);
    expect(getValueOptions(-1)).toEqual(["1"]);
});

test("datetime domain in readonly mode (check localization)", async () => {
    await makeMockServer({
        lang_parameters: {
            date_format: "%m.%d.%Y",
        },
    });
    mockTimeZone(+2);
    await makeDomainSelector({
        domain: `["&", ("datetime", ">=", "2023-11-03 11:41:23"), ("datetime", "<=", "2023-11-13 09:45:11")]`,
        readonly: true,
    });
    expect(".o_tree_editor_condition").toHaveText(
        `Datetime\nis between\n11.03.2023 13:41:23\nand\n11.13.2023 11:45:11`
    );
});

test("date domain in readonly mode (check localization)", async () => {
    await makeMockServer({
        lang_parameters: {
            date_format: "%d|%m|%Y",
        },
    });
    mockTimeZone(+2);
    await makeDomainSelector({
        domain: `["&", ("date", ">=", "2023-11-03"), ("date", "<=", "2023-11-13")]`,
        readonly: true,
    });
    expect(".o_tree_editor_condition").toHaveText("Date\nis between\n03|11|2023\nand\n13|11|2023");
});
