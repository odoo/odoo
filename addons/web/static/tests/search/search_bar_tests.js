/** @odoo-module **/

import * as dsHelpers from "@web/../tests/core/domain_selector_tests";
import {
    click,
    getFixture,
    getNodesTextContent,
    makeDeferred,
    nextTick,
    patchDate,
    patchTimeZone,
    triggerEvent,
} from "../helpers/utils";
import {
    editSearch,
    getFacetTexts,
    makeWithSearch,
    removeFacet,
    setupControlPanelServiceRegistry,
    toggleMenuItem,
    toggleSearchBarMenu,
    validateSearch,
} from "./helpers";

function getContext(controlPanel) {
    return controlPanel.env.searchModel.context;
}

function getDomain(controlPanel) {
    return controlPanel.env.searchModel.domain;
}

import { Component, onWillUpdateProps, xml } from "@odoo/owl";
import { SearchBar } from "@web/search/search_bar/search_bar";

let target;
let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        bar: { string: "Bar", type: "many2one", relation: "partner" },
                        birthday: { string: "Birthday", type: "date" },
                        birth_datetime: { string: "Birth DateTime", type: "datetime" },
                        foo: { string: "Foo", type: "char" },
                        bool: { string: "Bool", type: "boolean" },
                        company: { string: "Company", type: "many2one", relation: "partner" },
                        properties: {
                            string: "Properties",
                            type: "properties",
                            definition_record: "bar",
                            definition_record_field: "child_properties",
                        },
                        child_properties: { type: "properties_definition" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "First record",
                            foo: "yop",
                            bar: 2,
                            bool: true,
                            birthday: "1983-07-15",
                            birth_datetime: "1983-07-15 01:00:00",
                        },
                        {
                            id: 2,
                            display_name: "Second record",
                            foo: "blip",
                            bar: 1,
                            bool: false,
                            birthday: "1982-06-04",
                            birth_datetime: "1982-06-04 02:00:00",
                            company: 1,
                        },
                        {
                            id: 3,
                            display_name: "Third record",
                            foo: "gnap",
                            bar: 1,
                            bool: false,
                            birthday: "1985-09-13",
                            birth_datetime: "1985-09-13 03:00:00",
                            company: 5,
                        },
                        {
                            id: 4,
                            display_name: "Fourth record",
                            foo: "plop",
                            bar: 2,
                            bool: true,
                            birthday: "1983-05-05",
                            birth_datetime: "1983-05-05 04:00:00",
                        },
                        {
                            id: 5,
                            display_name: "Fifth record",
                            foo: "zoup",
                            bar: 2,
                            bool: true,
                            birthday: "1800-01-01",
                            birth_datetime: "1800-01-01 05:00:00",
                        },
                    ],
                },
            },
            views: {
                "partner,false,list": `<tree><field name="foo"/></tree>`,
                "partner,false,search": `
                    <search>
                        <field name="foo"/>
                        <field name="birthday"/>
                        <field name="birth_datetime"/>
                        <field name="bar" context="{'bar': self}"/>
                        <field name="company" domain="[('bool', '=', True)]"/>
                        <filter string="Birthday" name="date_filter" date="birthday"/>
                        <filter string="Birthday" name="date_group_by" context="{'group_by': 'birthday:day'}"/>
                    </search>
                `,
            },
            actions: {
                1: {
                    id: 1,
                    name: "Partners Action",
                    res_model: "partner",
                    search_view_id: [false, "search"],
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                },
            },
        };
        setupControlPanelServiceRegistry();
        target = getFixture();
    });

    QUnit.module("SearchBar");

    QUnit.test("basic rendering", async function (assert) {
        assert.expect(1);

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
        });

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_searchview input"),
            "searchview input should be focused"
        );
    });

    QUnit.test("navigation with facets", async function (assert) {
        assert.expect(4);

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            context: { search_default_date_group_by: 1 },
        });

        assert.containsOnce(
            target,
            ".o_searchview .o_searchview_facet",
            "there should be one facet"
        );
        assert.strictEqual(document.activeElement, target.querySelector(".o_searchview input"));

        // press left to focus the facet
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowLeft" });
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_searchview .o_searchview_facet")
        );

        // press right to focus the input
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowRight" });
        assert.strictEqual(document.activeElement, target.querySelector(".o_searchview input"));
    });

    QUnit.test("navigation with facets (2)", async function (assert) {
        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            context: {
                search_default_date_group_by: 1,
                search_default_foo: 1,
            },
        });

        assert.containsN(target, ".o_searchview .o_searchview_facet", 2);
        assert.strictEqual(document.activeElement, target.querySelector(".o_searchview input"));

        // press left to focus the rightmost facet
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowLeft" });
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_searchview .o_searchview_facet:nth-child(2)")
        );

        // press left to focus the leftmost facet
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowLeft" });
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_searchview .o_searchview_facet:nth-child(1)")
        );

        // press left to focus the input
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowLeft" });
        assert.strictEqual(document.activeElement, target.querySelector(".o_searchview input"));

        // press left to focus the leftmost facet
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowRight" });
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_searchview .o_searchview_facet:nth-child(1)")
        );
    });

    QUnit.test("search date and datetime fields. Support of timezones", async function (assert) {
        assert.expect(4);

        patchTimeZone(360);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
        });

        // Date case
        await editSearch(target, "07/15/1983");
        let searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" }); // select

        assert.deepEqual(
            getFacetTexts(target).map((str) => str.replace(/\s+/g, " ")),
            ["Birthday 07/15/1983"],
            "The format of the date in the facet should be in locale"
        );

        assert.deepEqual(getDomain(controlPanel), [["birthday", "=", "1983-07-15"]]);

        // Close Facet
        await click(target.querySelector(".o_searchview_facet .o_facet_remove"));

        // DateTime case
        await editSearch(target, "07/15/1983 00:00:00");
        searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" }); // select

        assert.deepEqual(
            getFacetTexts(target).map((str) => str.replace(/\s+/g, " ")),
            ["Birth DateTime 07/15/1983 00:00:00"],
            "The format of the datetime in the facet should be in locale"
        );

        assert.deepEqual(getDomain(controlPanel), [["birth_datetime", "=", "1983-07-14 18:00:00"]]);
    });

    QUnit.test("autocomplete menu clickout interactions", async function (assert) {
        assert.expect(9);

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="bar"/>
                        <field name="birthday"/>
                        <field name="birth_datetime"/>
                        <field name="foo"/>
                        <field name="bool"/>
                    </search>
                `,
        });

        const input = target.querySelector(".o_searchview input");

        assert.containsNone(target, ".o_searchview_autocomplete");

        await editSearch(target, "Hello there");

        assert.strictEqual(input.value, "Hello there", "input value should be updated");
        assert.containsOnce(target, ".o_searchview_autocomplete");

        await triggerEvent(input, null, "keydown", { key: "Escape" });

        assert.strictEqual(input.value, "", "input value should be empty");
        assert.containsNone(target, ".o_searchview_autocomplete");

        await editSearch(target, "General Kenobi");

        assert.strictEqual(input.value, "General Kenobi", "input value should be updated");
        assert.containsOnce(target, ".o_searchview_autocomplete");

        await click(document.body);

        assert.strictEqual(input.value, "", "input value should be empty");
        assert.containsNone(target, ".o_searchview_autocomplete");
    });

    QUnit.test("select an autocomplete field", async function (assert) {
        assert.expect(3);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
        });

        await editSearch(target, "a");
        assert.containsN(
            target,
            ".o_searchview_autocomplete li",
            3,
            "there should be 3 result for 'a' in search bar autocomplete"
        );

        const searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });
        assert.strictEqual(
            target.querySelector(".o_searchview_input_container .o_facet_values").innerText.trim(),
            "a",
            "There should be a field facet with label 'a'"
        );

        assert.deepEqual(getDomain(controlPanel), [["foo", "ilike", "a"]]);
    });

    QUnit.test("select an autocomplete field with `context` key", async function (assert) {
        assert.expect(8);

        let updateCount = 0;
        class TestComponent extends Component {
            setup() {
                onWillUpdateProps(() => {
                    updateCount++;
                });
            }
        }
        TestComponent.template = xml`<SearchBar/>`;
        TestComponent.components = { SearchBar };

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: TestComponent,
            searchMenuTypes: [],
            searchViewId: false,
        });

        // 'r' key to filter on bar "First Record"
        await editSearch(target, "record");
        const searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowRight" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });

        assert.deepEqual(
            getFacetTexts(target).map((str) => str.replace(/\s+/g, " ")),
            ["Bar First record"]
        );

        assert.strictEqual(updateCount, 1);

        assert.deepEqual(getDomain(controlPanel), [["bar", "=", 1]]);
        assert.deepEqual(controlPanel.env.searchModel.context.bar, [1]);

        // 'r' key to filter on bar "Second Record"
        await editSearch(target, "record");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowRight" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });

        assert.deepEqual(
            getFacetTexts(target).map((str) => str.replace(/\s+/g, " ")),
            ["Bar First record or Second record"]
        );

        assert.strictEqual(updateCount, 2);

        assert.deepEqual(getDomain(controlPanel), ["|", ["bar", "=", 1], ["bar", "=", 2]]);
        assert.deepEqual(controlPanel.env.searchModel.context.bar, [1, 2]);
    });

    QUnit.test("no search text triggers a reload", async function (assert) {
        assert.expect(2);

        let updateCount = 0;
        class TestComponent extends Component {
            setup() {
                onWillUpdateProps(() => {
                    updateCount++;
                });
            }
        }
        TestComponent.template = xml`<SearchBar/>`;
        TestComponent.components = { SearchBar };

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: TestComponent,
            searchMenuTypes: [],
            searchViewId: false,
        });

        const searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });

        assert.containsNone(target, ".o_searchview_facet_label");
        assert.strictEqual(updateCount, 1, "should have been updated once");
    });

    QUnit.test("selecting (no result) triggers a search bar rendering", async function (assert) {
        assert.expect(3);

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="bar"/>
                    </search>
                `,
        });

        await editSearch(target, "hello there");

        // 'a' key to filter nothing on bar
        const searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowRight" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });

        assert.strictEqual(
            target.querySelector(".o_searchview_autocomplete .focus").innerText.trim(),
            "(no result)",
            "there should be no result for 'a' in bar"
        );

        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });

        assert.containsNone(target, ".o_searchview_facet_label");
        assert.strictEqual(
            target.querySelector(".o_searchview input").value,
            "",
            "the search input should be re-rendered"
        );
    });

    QUnit.test(
        "update suggested filters in autocomplete menu with Japanese IME",
        async function (assert) {
            assert.expect(4);

            // The goal here is to simulate as many events happening during an IME
            // assisted composition session as possible. Some of these events are
            // not handled but are triggered to ensure they do not interfere.
            const TEST = "TEST";
            const テスト = "テスト";
            await makeWithSearch({
                serverData,
                resModel: "partner",
                Component: SearchBar,
                searchMenuTypes: [],
                searchViewId: false,
            });

            const searchInput = target.querySelector(".o_searchview input");

            // Simulate typing "TEST" on search view.
            for (let i = 0; i < TEST.length; i++) {
                const key = TEST[i].toUpperCase();
                await triggerEvent(searchInput, null, "keydown", {
                    key,
                    isComposing: true,
                });
                if (i === 0) {
                    // Composition is initiated after the first keydown
                    await triggerEvent(searchInput, null, "compositionstart");
                }
                await triggerEvent(searchInput, null, "keypress", {
                    key,
                    isComposing: true,
                });
                searchInput.value = TEST.slice(0, i + 1);
                await triggerEvent(searchInput, null, "keyup", { key, isComposing: true });
                await triggerEvent(searchInput, null, "input", {
                    inputType: "insertCompositionText",
                    isComposing: true,
                });
            }
            assert.containsOnce(
                target,
                ".o_searchview_autocomplete",
                "should display autocomplete dropdown menu on typing something in search view"
            );
            assert.strictEqual(
                target.querySelector(".o_searchview_autocomplete li").innerText.trim(),
                "Search Foo for: TEST",
                `1st filter suggestion should be based on typed word "TEST"`
            );

            // Simulate soft-selection of another suggestion from IME through keyboard navigation.
            await triggerEvent(searchInput, null, "keydown", {
                key: "ArrowDown",
                isComposing: true,
            });
            await triggerEvent(searchInput, null, "keypress", {
                key: "ArrowDown",
                isComposing: true,
            });
            searchInput.value = テスト;
            await triggerEvent(searchInput, null, "keyup", {
                key: "ArrowDown",
                isComposing: true,
            });
            await triggerEvent(searchInput, null, "input", {
                inputType: "insertCompositionText",
                isComposing: true,
            });

            assert.strictEqual(
                target.querySelector(".o_searchview_autocomplete li").innerText.trim(),
                "Search Foo for: テスト",
                `1st filter suggestion should be updated with soft-selection typed word "テスト"`
            );

            // Simulate selection on suggestion item "TEST" from IME.
            await triggerEvent(searchInput, null, "keydown", {
                key: "Enter",
                isComposing: true,
            });
            await triggerEvent(searchInput, null, "keypress", {
                key: "Enter",
                isComposing: true,
            });
            searchInput.value = TEST;
            await triggerEvent(searchInput, null, "keyup", {
                key: "Enter",
                isComposing: true,
            });
            await triggerEvent(searchInput, null, "input", {
                inputType: "insertCompositionText",
                isComposing: true,
            });

            // End of the composition
            await triggerEvent(searchInput, null, "compositionend");

            assert.strictEqual(
                target.querySelector(".o_searchview_autocomplete li").innerText.trim(),
                "Search Foo for: TEST",
                `1st filter suggestion should finally be updated with click selection on word "TEST" from IME`
            );
        }
    );

    QUnit.test("open search view autocomplete on paste value using mouse", async function (assert) {
        assert.expect(1);

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
        });

        // Simulate paste text through the mouse.
        const searchInput = target.querySelector(".o_searchview input");
        searchInput.value = "ABC";
        await triggerEvent(searchInput, null, "input", { inputType: "insertFromPaste" });
        assert.containsOnce(
            target,
            ".o_searchview_autocomplete",
            "should display autocomplete dropdown menu on paste in search view"
        );
    });

    QUnit.test("select autocompleted many2one", async function (assert) {
        assert.expect(4);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="foo"/>
                        <field name="birthday"/>
                        <field name="birth_datetime"/>
                        <field name="bar" operator="child_of"/>
                    </search>
                `,
        });

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "rec");
        await click(target.querySelector(".o_searchview_autocomplete li:last-child"));

        assert.deepEqual(getDomain(controlPanel), [["bar", "child_of", "rec"]]);

        await removeFacet(target);

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "rec");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector(".o_searchview_autocomplete li.o_menu_item.o_indent"));

        assert.deepEqual(getDomain(controlPanel), [["bar", "child_of", 1]]);
    });

    QUnit.test('"null" as autocomplete value', async function (assert) {
        assert.expect(3);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
        });

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "null");

        assert.strictEqual(
            target.querySelector(".o_searchview_autocomplete .focus").innerText,
            "Search Foo for: null"
        );

        await click(target.querySelector(".o_searchview_autocomplete li.focus a"));

        assert.deepEqual(getDomain(controlPanel), [["foo", "ilike", "null"]]);
    });

    QUnit.test("autocompletion with a boolean field", async function (assert) {
        assert.expect(8);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="bool"/>
                    </search>
                `,
        });

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "y");

        assert.containsN(target, ".o_searchview_autocomplete li", 1);
        assert.strictEqual(
            target.querySelector(".o_searchview_autocomplete li:last-child").innerText,
            "Search Bool for: Yes"
        );

        // select "Yes"
        await click(target.querySelector(".o_searchview_autocomplete li:last-child"));

        assert.deepEqual(getDomain(controlPanel), [["bool", "=", true]]);

        await removeFacet(target);

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "No");

        assert.containsN(target, ".o_searchview_autocomplete li", 1);
        assert.strictEqual(
            target.querySelector(".o_searchview_autocomplete li:last-child").innerText,
            "Search Bool for: No"
        );

        // select "No"
        await click(target.querySelector(".o_searchview_autocomplete li:last-child"));

        assert.deepEqual(getDomain(controlPanel), [["bool", "=", false]]);
    });

    QUnit.test("the search value is trimmed to remove unnecessary spaces", async function (assert) {
        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                        <search>
                            <field name="foo" filter_domain="[('foo', 'ilike', self)]"/>
                        </search>
                    `,
        });
        await editSearch(target, "bar");
        await validateSearch(target);

        assert.deepEqual(getDomain(controlPanel), [["foo", "ilike", "bar"]]);

        await removeFacet(target);

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "   bar ");
        await validateSearch(target);

        assert.deepEqual(
            getDomain(controlPanel),
            [["foo", "ilike", "bar"]],
            "the value has been trimmed"
        );
    });

    QUnit.test("reference fields are supported in search view", async function (assert) {
        assert.expect(4);

        const partnerModel = serverData.models.partner;
        partnerModel.fields.ref = { type: "reference", string: "Reference" };
        partnerModel.records.forEach((record, i) => {
            record.ref = `ref${String(i).padStart(3, "0")}`;
        });

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="ref"/>
                    </search>
                `,
        });

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "ref");
        await validateSearch(target);

        assert.deepEqual(getDomain(controlPanel), [["ref", "ilike", "ref"]]);

        await removeFacet(target);

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "ref002");
        await validateSearch(target);

        assert.deepEqual(getDomain(controlPanel), [["ref", "ilike", "ref002"]]);
    });

    QUnit.test(
        "expand an asynchronous menu and change the selected item with the mouse during expansion",
        async function (assert) {
            assert.expect(2);

            const def = makeDeferred();
            const mockRPC = async (route) => {
                if (route.includes("/partner/name_search")) {
                    await def;
                }
            };
            await makeWithSearch({
                serverData,
                mockRPC,
                resModel: "partner",
                Component: SearchBar,
                searchMenuTypes: [],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <field name="bar" operator="child_of"/>
                    </search>
                `,
            });
            await editSearch(target, "rec");
            await click(target.querySelector(".o_expand"));
            await triggerEvent(
                target,
                ".o_searchview_autocomplete li.o_menu_item:first-child",
                "mousemove"
            );
            assert.containsNone(target, ".o_searchview_autocomplete li.o_menu_item.o_indent");

            def.resolve();
            await nextTick();
            assert.containsN(target, ".o_searchview_autocomplete li.o_menu_item.o_indent", 5);
        }
    );

    QUnit.test(
        "expand an asynchronous menu and change the selected item with the arrow during expansion",
        async function (assert) {
            assert.expect(2);

            const def = makeDeferred();
            const mockRPC = async (route) => {
                if (route.includes("/partner/name_search")) {
                    await def;
                }
            };
            await makeWithSearch({
                serverData,
                mockRPC,
                resModel: "partner",
                Component: SearchBar,
                searchMenuTypes: [],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <field name="bar" operator="child_of"/>
                    </search>
                `,
            });
            await editSearch(target, "rec");
            await click(target.querySelector(".o_expand"));
            const searchInput = target.querySelector(".o_searchview input");
            await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
            assert.containsNone(target, ".o_searchview_autocomplete li.o_menu_item.o_indent");

            def.resolve();
            await nextTick();
            assert.containsN(target, ".o_searchview_autocomplete li.o_menu_item.o_indent", 5);
        }
    );

    QUnit.test("checks that an arrowDown always selects an item", async function (assert) {
        assert.expect(1);

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="bar" operator="child_of"/>
                    </search>
                `,
        });
        await editSearch(target, "rec");
        await click(target.querySelector(".o_expand"));
        click(target.querySelector(".o_expand"));
        triggerEvent(
            target,
            ".o_searchview_autocomplete li.o_menu_item.o_indent:last-child",
            "mousemove"
        );
        const searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        assert.containsOnce(target, ".focus");
    });

    QUnit.test("checks that an arrowUp always selects an item", async function (assert) {
        assert.expect(1);

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="bar" operator="child_of"/>
                    </search>
                `,
        });
        await editSearch(target, "rec");
        await click(target.querySelector(".o_expand"));
        click(target.querySelector(".o_expand"));
        triggerEvent(
            target,
            ".o_searchview_autocomplete li.o_menu_item.o_indent:last-child",
            "mousemove"
        );
        const searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowUp" });
        assert.containsOnce(target, ".focus");
    });

    QUnit.test("many2one_reference fields are supported in search view", async function (assert) {
        serverData.models.partner.fields.res_id = {
            string: "Resource ID",
            type: "many2one_reference",
        };

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: /*xml*/ `
                <search>
                    <field name="foo" />
                    <field name="res_id" />
                </search>
            `,
        });

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "12");
        assert.deepEqual(
            [...target.querySelectorAll(".o_searchview ul li.dropdown-item")].map(
                (el) => el.innerText
            ),
            ["Search Foo for: 12", "Search Resource ID for: 12"]
        );
        await triggerEvent(target.querySelector(".o_searchview input"), null, "keydown", {
            key: "ArrowDown",
        });
        await validateSearch(target);
        assert.deepEqual(getDomain(controlPanel), [["res_id", "=", 12]]);

        await removeFacet(target);
        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(target, "1a");
        assert.deepEqual(
            [...target.querySelectorAll(".o_searchview ul li.dropdown-item")].map(
                (el) => el.innerText
            ),
            ["Search Foo for: 1a"]
        );
        await validateSearch(target);
        assert.deepEqual(getDomain(controlPanel), [["foo", "ilike", "1a"]]);
    });

    QUnit.test("check kwargs of a rpc call with a domain", async function (assert) {
        assert.expect(3);

        const mockRPC = async (route, args) => {
            if (route.includes("/partner/name_search")) {
                assert.deepEqual(args, {
                    model: "partner",
                    method: "name_search",
                    args: [],
                    kwargs: {
                        args: [["bool", "=", true]],
                        context: { lang: "en", uid: 7, tz: "taht" },
                        limit: 8,
                        name: "F",
                    },
                });
            }
        };

        const controlPanel = await makeWithSearch({
            serverData,
            mockRPC,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
        });

        await editSearch(target, "F");
        assert.containsN(
            target,
            ".o_searchview_autocomplete li",
            3,
            "there should be 3 result for 'F' in search bar autocomplete"
        );

        const searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowRight" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });
        assert.deepEqual(getDomain(controlPanel), [["company", "=", 5]]);
    });

    QUnit.test("should wait label promises for one2many search defaults", async function (assert) {
        assert.expect(3);

        const target = getFixture();

        const def = makeDeferred();
        const mockRPC = async (_, args) => {
            if (args.method === "read") {
                await def;
            }
        };

        makeWithSearch({
            serverData,
            mockRPC,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            context: { search_default_company: 1 },
        });

        await nextTick();
        assert.containsNone(target, ".o_cp_searchview");

        def.resolve();
        await nextTick();
        assert.containsOnce(target, ".o_cp_searchview");
        assert.strictEqual(getFacetTexts(target)[0].replace("\n", ""), "CompanyFirst record");
    });

    QUnit.test("globalContext keys in name_search", async function (assert) {
        assert.expect(1);

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                <search>
                    <field name="company"/>
                </search>
            `,
            context: { specialKey: "ABCD" },
            mockRPC(_, args) {
                if (args.method === "name_search") {
                    assert.strictEqual(args.kwargs.context.specialKey, "ABCD");
                }
            },
        });

        await editSearch(target, "F");
        await triggerEvent(target, ".o_searchview input", "keydown", { key: "ArrowRight" });
    });

    QUnit.test("search a property", async function (assert) {
        assert.expect(57);

        async function mockRPC(_, { method, model, kwargs }) {
            if (
                method === "web_search_read" &&
                model === "partner" &&
                kwargs.specification.display_name &&
                kwargs.specification.child_properties
            ) {
                const definition1 = [
                    {
                        type: "many2one",
                        string: "My Partner",
                        name: "my_partner",
                        comodel: "partner",
                    },
                    {
                        type: "many2many",
                        string: "My Partners",
                        name: "my_partners",
                        comodel: "partner",
                    },
                    {
                        type: "selection",
                        string: "My Selection",
                        name: "my_selection",
                        selection: [
                            ["a", "A"],
                            ["b", "B"],
                            ["c", "C"],
                            ["aa", "AA"],
                        ],
                    },
                    {
                        type: "tags",
                        string: "My Tags",
                        name: "my_tags",
                        tags: [
                            ["a", "A", 1],
                            ["b", "B", 5],
                            ["c", "C", 3],
                            ["aa", "AA", 2],
                        ],
                    },
                ];

                const definition2 = [
                    {
                        type: "char",
                        string: "My Text",
                        name: "my_text",
                    },
                ];

                return {
                    records: [
                        { id: 1, display_name: "Bar 1", child_properties: definition1 },
                        { id: 2, display_name: "Bar 2", child_properties: definition2 },
                    ],
                };
            } else if (method === "name_search" && model === "partner" && kwargs.name === "Bo") {
                return [
                    [5, "Bob"],
                    [6, "Bobby"],
                ];
            } else if (method === "name_search" && model === "partner" && kwargs.name === "Ali") {
                return [
                    [9, "Alice"],
                    [10, "Alicia"],
                ];
            }
        }

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="properties"/>
                    </search>
                `,
            mockRPC,
        });

        // expand the properties field
        await editSearch(target, "a");

        await click(target.querySelector(".o_expand"));

        let items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 8);
        assert.strictEqual(items[0].innerText, "Search Properties");
        assert.strictEqual(items[1].innerText, "My Partner (Bar 1)");
        assert.strictEqual(items[3].innerText, "My Selection (Bar 1) for: A");
        assert.strictEqual(items[4].innerText, "My Selection (Bar 1) for: AA");
        assert.strictEqual(items[5].innerText, "My Tags (Bar 1) for: A");
        assert.strictEqual(items[6].innerText, "My Tags (Bar 1) for: AA");
        assert.strictEqual(items[7].innerText, "My Text (Bar 2) for: a");

        // click again on the expand icon to hide the properties
        await click(target.querySelector(".o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 1, "Should have hidden the properties");

        // search for a partner, and expand the many2many property
        await editSearch(target, "Bo");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector("li:nth-child(3) .o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 6);
        assert.strictEqual(items[3].innerText, "Bob");
        assert.strictEqual(items[4].innerText, "Bobby");

        // fold all the properties (included the search result)
        await click(target.querySelector(".o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 1, "Should have folded the properties");

        // unfold all the properties but fold the search result
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector("li:nth-child(3) .o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 4, "Should have unfolded the properties");
        assert.strictEqual(items[1].innerText, "My Partner (Bar 1)");
        assert.strictEqual(items[2].innerText, "My Partners (Bar 1)");
        assert.strictEqual(items[3].innerText, "My Text (Bar 2) for: Bo");

        // select Bobby
        await click(target.querySelector("li:nth-child(3) .o_expand"));
        await click(target.querySelector(".o_searchview_input_container li:nth-child(5)"));
        assert.deepEqual(getDomain(controlPanel), [
            "&",
            ["bar", "=", 1],
            ["properties.my_partners", "in", 6],
        ]);

        // expand the selection properties
        await click(target.querySelector(".o_cp_searchview"));
        await editSearch(target, "a");
        await click(target.querySelector(".o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 8, "Should have unfolded the selection properties");
        assert.strictEqual(items[3].innerText, "My Selection (Bar 1) for: A");
        assert.strictEqual(items[4].innerText, "My Selection (Bar 1) for: AA");

        // select the selection option "AA"
        await click(target.querySelector(".o_searchview_input_container li:nth-child(5)"));
        let expectedDomain = [
            "&",
            "&",
            ["bar", "=", 1],
            ["properties.my_partners", "in", 6],
            "&",
            ["bar", "=", 1],
            ["properties.my_selection", "=", "aa"],
        ];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);

        // select the selection option "A"
        await click(target.querySelector(".o_cp_searchview"));
        await editSearch(target, "a");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector(".o_searchview_input_container li:nth-child(4)"));
        expectedDomain = [
            "&",
            "&",
            ["bar", "=", 1],
            ["properties.my_partners", "in", 6],
            "|",
            "&",
            ["bar", "=", 1],
            ["properties.my_selection", "=", "aa"],
            "&",
            ["bar", "=", 1],
            ["properties.my_selection", "=", "a"],
        ];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);

        // reset the search
        await click(target.querySelector(".o_facet_remove"));
        await click(target.querySelector(".o_facet_remove"));

        // search a many2one value
        await click(target.querySelector(".o_cp_searchview"));
        await editSearch(target, "Ali");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector("li:nth-child(2) .o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 6, "Should show the search result");
        assert.strictEqual(items[2].innerText, "Alice");
        assert.strictEqual(items[3].innerText, "Alicia");
        await click(target.querySelector(".o_searchview_input_container li:nth-child(4)"));
        expectedDomain = ["&", ["bar", "=", 1], ["properties.my_partner", "=", 10]];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);

        // search a tag value
        await click(target.querySelector(".o_cp_searchview"));
        await editSearch(target, "A");
        await click(target.querySelector(".o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 8, "Should show the search result");
        assert.strictEqual(items[5].innerText, "My Tags (Bar 1) for: A");
        assert.strictEqual(items[6].innerText, "My Tags (Bar 1) for: AA");

        await click(target.querySelector(".o_searchview_input_container li:nth-child(7)"));
        expectedDomain = [
            "&",
            "&",
            ["bar", "=", 1],
            ["properties.my_partner", "=", 10],
            "&",
            ["bar", "=", 1],
            ["properties.my_tags", "in", "aa"],
        ];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);
        // add the tag "B"
        await click(target.querySelector(".o_cp_searchview"));
        await editSearch(target, "B");
        await click(target.querySelector(".o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 6, "Should show the search result");
        assert.strictEqual(items[4].innerText, "My Tags (Bar 1) for: B");
        await click(target.querySelector(".o_searchview_input_container li:nth-child(5)"));
        expectedDomain = [
            "&",
            "&",
            ["bar", "=", 1],
            ["properties.my_partner", "=", 10],
            "|",
            "&",
            ["bar", "=", 1],
            ["properties.my_tags", "in", "aa"],
            "&",
            ["bar", "=", 1],
            ["properties.my_tags", "in", "b"],
        ];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);

        // try to click on the many2one properties without unfolding
        // it should not add the domain, but unfold the item
        await editSearch(target, "Bobby");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector(".o_searchview_input_container li:nth-child(2)"));
        assert.deepEqual(getDomain(controlPanel), expectedDomain);
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 5, "Should have unfold the many2one");
        assert.strictEqual(items[2].innerText, "(no result)", "Should have unfold the many2one");

        // test the navigation with keyboard
        await editSearch(target, "Bo");
        const focusedItem = () => {
            return target.querySelector(".o_menu_item.focus");
        };
        assert.strictEqual(focusedItem().innerText, "Search Properties");
        // unfold the properties field
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowRight" });
        assert.strictEqual(focusedItem().innerText, "Search Properties");
        assert.ok(focusedItem().querySelector(".fa-caret-down"));
        // move on the many2one property
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowRight" });
        assert.strictEqual(focusedItem().innerText, "My Partner (Bar 1)");
        assert.ok(focusedItem().querySelector(".fa-caret-right"));
        // move on the many2many property
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowDown" });
        assert.strictEqual(focusedItem().innerText, "My Partners (Bar 1)");
        assert.ok(focusedItem().querySelector(".fa-caret-right"));
        // move on the many2one property again
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowUp" });
        assert.strictEqual(focusedItem().innerText, "My Partner (Bar 1)");
        assert.ok(focusedItem().querySelector(".fa-caret-right"));
        // unfold the many2one
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowRight" });
        assert.strictEqual(focusedItem().innerText, "My Partner (Bar 1)");
        assert.ok(focusedItem().querySelector(".fa-caret-down"));
        // select the first many2one
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowRight" });
        assert.strictEqual(focusedItem().innerText, "Bob");
        // go up on the parent
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowLeft" });
        assert.strictEqual(focusedItem().innerText, "My Partner (Bar 1)");
        assert.ok(focusedItem().querySelector(".fa-caret-down"));
        // fold the parent
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowLeft" });
        assert.strictEqual(focusedItem().innerText, "My Partner (Bar 1)");
        assert.ok(focusedItem().querySelector(".fa-caret-right"));
        // go up on the properties field
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowLeft" });
        assert.strictEqual(focusedItem().innerText, "Search Properties");
        assert.ok(focusedItem().querySelector(".fa-caret-down"));
        // fold the properties field
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowLeft" });
        assert.strictEqual(focusedItem().innerText, "Search Properties");
        assert.ok(focusedItem().querySelector(".fa-caret-right"));
    });

    QUnit.test("search a property: definition record id in the context", async function (assert) {
        assert.expect(3);

        async function mockRPC(route, { method, model, args, kwargs }) {
            if (
                method === "web_search_read" &&
                model === "partner" &&
                kwargs.specification.display_name &&
                kwargs.specification.child_properties
            ) {
                assert.deepEqual(
                    kwargs.domain,
                    ["&", ["child_properties", "!=", false], ["id", "=", 2]],
                    "Should search only the active parent properties"
                );

                const definition2 = [
                    {
                        type: "char",
                        string: "My Text",
                        name: "my_text",
                    },
                ];

                return {
                    records: [{ id: 2, display_name: "Bar 2", child_properties: definition2 }],
                };
            }
        }

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="properties"/>
                    </search>
                `,
            mockRPC,
            context: { active_id: 2 },
        });

        await click(target.querySelector(".o_cp_searchview"));
        await editSearch(target, "a");
        await click(target.querySelector(".o_expand"));

        const items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 2, "Should show the search result");
        assert.strictEqual(items[1].innerText, "My Text (Bar 2) for: a");
    });

    QUnit.test("edit a filter", async function (assert) {
        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: ["groupBy"], // we need it to have facet (see facets getter in search_model)
            searchViewId: false,
            searchViewArch: `
                <search>
                    <filter name="filter" string="Filter" domain="[('birthday', '>=', context_today())]"/>
                    <filter name="bool" string="Bool" domain="[]" context="{'group_by': 'bool'}"/>
                </search>
            `,
            context: {
                search_default_filter: true,
                search_default_bool: true,
            },
            mockRPC(route) {
                if (route === "/web/domain/validate") {
                    return true;
                }
            },
        });
        assert.deepEqual(getFacetTexts(target), ["Filter", "Bool"]);
        assert.containsN(target, ".o_searchview_facet .o_searchview_facet_label", 2);
        assert.containsOnce(
            target,
            ".o_searchview_facet.o_facet_with_domain .o_searchview_facet_label"
        );
        assert.containsNone(target, ".modal");

        await click(target, ".o_facet_with_domain .o_searchview_facet_label");
        assert.containsOnce(target, ".modal");
        assert.strictEqual(target.querySelector(".modal header").innerText, "Modify Condition");
        assert.containsOnce(target, ".modal .o_domain_selector");
        assert.containsOnce(target, dsHelpers.SELECTORS.condition);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".modal footer button")), [
            "Confirm",
            "Discard",
        ]);
        assert.strictEqual(dsHelpers.getCurrentPath(target), "Birthday");
        assert.strictEqual(dsHelpers.getCurrentOperator(target), ">=");
        assert.strictEqual(dsHelpers.getCurrentValue(target), "context_today()");
        assert.notOk(target.querySelector(".modal footer button").disabled);

        await dsHelpers.clickOnButtonDeleteNode(target);
        assert.containsNone(target, dsHelpers.SELECTORS.condition);
        assert.ok(target.querySelector(".modal footer button").disabled);

        await click(target, `.modal ${dsHelpers.SELECTORS.addNewRule}`);
        assert.containsOnce(target, dsHelpers.SELECTORS.condition);
        assert.strictEqual(dsHelpers.getCurrentPath(target), "ID");
        assert.strictEqual(dsHelpers.getCurrentOperator(target), "=");
        assert.strictEqual(dsHelpers.getCurrentValue(target), "1");

        await click(target.querySelector(".modal footer button"));
        assert.containsNone(target, ".modal");
        assert.deepEqual(getFacetTexts(target), ["Bool", "ID = 1"]);
    });

    QUnit.test(
        "edit a filter with context: context is kept after edition",
        async function (assert) {
            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "partner",
                Component: SearchBar,
                searchViewId: false,
                searchViewArch: `
                <search>
                    <filter name="filter" string="Filter"  context="{'specialKey': 'abc'}" domain="[('foo', '=', 'abc')]"/>
                </search>
            `,
                context: {
                    search_default_filter: true,
                },
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            assert.deepEqual(getFacetTexts(target), ["Filter"]);
            assert.deepEqual(getContext(controlPanel).specialKey, "abc");

            await click(target, ".o_facet_with_domain .o_searchview_facet_label");
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), [`Foo = abc`]);
            assert.deepEqual(getContext(controlPanel).specialKey, "abc");
        }
    );

    QUnit.test("edit a favorite", async function (assert) {
        const irFilters = [
            {
                context: "{ 'some_key': 'some_value', 'group_by': ['bool'] }",
                domain: "[('foo', 'ilike', 'abc')]",
                id: 1,
                is_default: true,
                name: "My favorite",
                sort: "[]",
                user_id: [2, "Mitchell Admin"],
            },
        ];
        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: ["groupBy"], // we need it to have facet (see facets getter in search_model)
            searchViewId: false,
            searchViewArch: `
                <search>
                    <filter name="company" string="Company" domain="[]" context="{'group_by': 'company'}"/>
                </search>
            `,
            irFilters,
            mockRPC(route) {
                if (route === "/web/domain/validate") {
                    return true;
                }
            },
        });
        assert.deepEqual(getFacetTexts(target), ["My favorite"]);
        assert.containsOnce(
            target,
            ".o_searchview_facet.o_facet_with_domain .o_searchview_facet_label"
        );

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Company");

        assert.deepEqual(getFacetTexts(target), ["My favorite", "Company"]);

        assert.containsN(target, ".o_searchview_facet .o_searchview_facet_label", 2);
        assert.containsOnce(
            target,
            ".o_searchview_facet.o_facet_with_domain .o_searchview_facet_label"
        );

        await click(target, ".o_facet_with_domain .o_searchview_facet_label");
        assert.containsOnce(target, ".modal");
        assert.strictEqual(dsHelpers.getCurrentPath(target), "Foo");
        assert.strictEqual(dsHelpers.getCurrentOperator(target), "contains");
        assert.strictEqual(dsHelpers.getCurrentValue(target), "abc");

        await click(target.querySelector(".modal footer button"));
        assert.containsNone(target, ".modal");
        assert.deepEqual(getFacetTexts(target), ["Bool\n>\nCompany", "Foo contains abc"]);
    });

    QUnit.test("edit a date filter with comparison active", async function (assert) {
        patchDate(2023, 3, 28, 13, 40, 0);
        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchMenuTypes: ["filter", "comparison"],
            searchViewId: false,
            searchViewArch: `
                <search>
                    <filter name="birthday" string="Birthday" date="birthday"/>
                </search>
            `,
            context: {
                search_default_birthday: true,
            },
            mockRPC(route) {
                if (route === "/web/domain/validate") {
                    return true;
                }
            },
        });
        assert.deepEqual(getFacetTexts(target), ["Birthday: April 2023"]);
        assert.containsOnce(
            target,
            ".o_searchview_facet.o_facet_with_domain .o_searchview_facet_label"
        );

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Birthday: Previous Period");

        assert.deepEqual(getFacetTexts(target), [
            "Birthday: April 2023",
            "Birthday: Previous Period",
        ]);
        assert.containsOnce(
            target,
            ".o_searchview_facet.o_facet_with_domain .o_searchview_facet_label"
        );

        await click(target, ".o_facet_with_domain .o_searchview_facet_label");
        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, dsHelpers.SELECTORS.condition);
        assert.strictEqual(dsHelpers.getCurrentPath(target), "Birthday");
        assert.strictEqual(dsHelpers.getCurrentOperator(target), "is between");
        assert.deepEqual(
            [...target.querySelectorAll(`.o_datetime_input`)].map((el) => el.value),
            ["04/01/2023", "04/30/2023"]
        );

        await click(target.querySelector(".modal footer button"));
        assert.containsNone(target, ".modal");
        assert.deepEqual(getFacetTexts(target), [`Birthday is between 2023-04-01 and 2023-04-30`]);
    });

    QUnit.test("edit a field", async function (assert) {
        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchViewId: false,
            searchViewArch: `
                <search>
                    <field name="foo"/>
                </search>
            `,
            context: {
                search_default_foo: "abc",
            },
            mockRPC(route) {
                if (route === "/web/domain/validate") {
                    return true;
                }
            },
        });
        assert.deepEqual(getFacetTexts(target), ["Foo\nabc"]);
        assert.containsOnce(
            target,
            ".o_searchview_facet.o_facet_with_domain .o_searchview_facet_label"
        );

        await editSearch(target, "def");
        const searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" }); // select

        assert.deepEqual(getFacetTexts(target), ["Foo\nabc\nor\ndef"]);

        await click(target, ".o_facet_with_domain .o_searchview_facet_label");
        assert.containsN(target, dsHelpers.SELECTORS.condition, 2);

        assert.strictEqual(dsHelpers.getCurrentPath(target), "Foo");
        assert.strictEqual(dsHelpers.getCurrentOperator(target), "contains");
        assert.strictEqual(dsHelpers.getCurrentValue(target), "abc");

        assert.strictEqual(dsHelpers.getCurrentPath(target, 1), "Foo");
        assert.strictEqual(dsHelpers.getCurrentOperator(target, 1), "contains");
        assert.strictEqual(dsHelpers.getCurrentValue(target, 1), "def");

        await click(target.querySelector(".modal footer button"));

        assert.deepEqual(getFacetTexts(target), [`Foo contains abc or Foo contains def`]);
    });

    QUnit.test("no rpc for getting display_name for facets if known", async function (assert) {
        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: SearchBar,
            searchViewId: false,
            searchViewArch: `
                <search>
                    <filter name="filter" string="Filter" domain="[('bar', 'in', [])]"/>
                </search>
            `,
            context: {
                search_default_filter: true,
            },
            mockRPC(route, { method, kwargs }) {
                assert.step(method || route);
                if (route === "/web/domain/validate") {
                    return true;
                }
                if (method === "name_search") {
                    assert.step(JSON.stringify(kwargs.args /** domain */));
                }
            },
        });
        assert.deepEqual(getFacetTexts(target), ["Filter"]);
        assert.verifySteps([`get_views`]);

        await click(target, ".o_facet_with_domain .o_searchview_facet_label");
        assert.verifySteps([`fields_get`]);

        await click(target, ".o-autocomplete--input");
        assert.verifySteps([`name_search`, `["!",["id","in",[]]]`]);

        await click(target.querySelector(".dropdown-menu li"));
        await click(target.querySelector(".modal footer button"));
        assert.deepEqual(getFacetTexts(target), ["Bar is in ( First record )"]);
        assert.verifySteps([`/web/domain/validate`]);
    });
});
