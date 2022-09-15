/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import {
    click,
    getFixture,
    makeDeferred,
    nextTick,
    patchTimeZone,
    patchWithCleanup,
    triggerEvent,
} from "../helpers/utils";
import {
    editSearch,
    getFacetTexts,
    makeWithSearch,
    removeFacet,
    setupControlPanelServiceRegistry,
    validateSearch,
} from "./helpers";

function getDomain(controlPanel) {
    return controlPanel.env.searchModel.domain;
}

const { onWillUpdateProps } = owl;

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
                        properties: {
                            string: "Properties",
                            type: "properties",
                            definition_record: "bar",
                            definition_record_field: "child_properties",
                        },
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
                        },
                        {
                            id: 3,
                            display_name: "Third record",
                            foo: "gnap",
                            bar: 1,
                            bool: false,
                            birthday: "1985-09-13",
                            birth_datetime: "1985-09-13 03:00:00",
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
            Component: ControlPanel,
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
            Component: ControlPanel,
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
            Component: ControlPanel,
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
            Component: ControlPanel,
            searchMenuTypes: [],
            searchViewId: false,
        });

        // Date case
        await editSearch(target, "07/15/1983");
        let searchInput = target.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" }); // select

        assert.deepEqual(
            getFacetTexts(target).map((str) => str.replace(/\s+/, " ")),
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
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" }); // select

        assert.deepEqual(
            getFacetTexts(target).map((str) => str.replace(/\s+/, " ")),
            ["Birth DateTime\n07/15/1983 00:00:00"],
            "The format of the datetime in the facet should be in locale"
        );

        assert.deepEqual(getDomain(controlPanel), [["birth_datetime", "=", "1983-07-14 18:00:00"]]);
    });

    QUnit.test("autocomplete menu clickout interactions", async function (assert) {
        assert.expect(9);

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
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
            Component: ControlPanel,
            searchMenuTypes: [],
            searchViewId: false,
        });

        await editSearch(target, "a");
        assert.containsN(
            target,
            ".o_searchview_autocomplete li",
            2,
            "there should be 2 result for 'a' in search bar autocomplete"
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
        patchWithCleanup(ControlPanel.prototype, {
            setup() {
                this._super();
                onWillUpdateProps(() => {
                    updateCount++;
                });
            },
        });

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
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
            getFacetTexts(target).map((str) => str.replace(/\s+/, "")),
            ["BarFirst record"]
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
            getFacetTexts(target).map((str) => str.replace(/\s+/, "")),
            ["BarFirst recordorSecond record"]
        );

        assert.strictEqual(updateCount, 2);

        assert.deepEqual(getDomain(controlPanel), ["|", ["bar", "=", 1], ["bar", "=", 2]]);
        assert.deepEqual(controlPanel.env.searchModel.context.bar, [1, 2]);
    });

    QUnit.test("no search text triggers a reload", async function (assert) {
        assert.expect(2);

        let updateCount = 0;
        patchWithCleanup(ControlPanel.prototype, {
            setup() {
                this._super();
                onWillUpdateProps(() => {
                    updateCount++;
                });
            },
        });

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
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
            Component: ControlPanel,
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
                Component: ControlPanel,
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
            Component: ControlPanel,
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
            Component: ControlPanel,
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
            Component: ControlPanel,
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
            Component: ControlPanel,
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
            Component: ControlPanel,
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
            Component: ControlPanel,
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
                Component: ControlPanel,
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
                Component: ControlPanel,
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
            Component: ControlPanel,
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
            Component: ControlPanel,
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

    QUnit.test("search a property: basic", async function (assert) {
        assert.expect(29);

        async function mockRPC(route, { method, model, args, kwargs }) {
            if (method === "search_read" && model === "partner"
                && args[1][0] === "display_name" && args[1][1] === "child_properties") {

                const definition1 = [{
                    'type': 'many2one',
                    'string': 'My Partner',
                    'name': 'my_partner',
                    'comodel': 'partner',
                }, {
                    'type': 'many2many',
                    'string': 'My Partners',
                    'name': 'my_partners',
                    'comodel': 'partner',
                }, {
                    'type': 'selection',
                    'string': 'My Selection',
                    'name': 'my_selection',
                    'selection': [['a', 'A'], ['b', 'B'], ['c', 'C'], ['aa', 'AA']],
                }, {
                    'type': 'tags',
                    'string': 'My Tags',
                    'name': 'my_tags',
                    'tags': [['a', 'A', 1], ['b', 'B', 5], ['c', 'C', 3], ['aa', 'AA', 2]],
                }];

                const definition2 = [{
                    'type': 'char',
                    'string': 'My Text',
                    'name': 'my_text',
                }];

                return [
                    {'id': 1, 'display_name': 'Bar 1', 'child_properties': definition1},
                    {'id': 2, 'display_name': 'Bar 2', 'child_properties': definition2},
                ];
            } else if (method === "name_search" && model === "partner" && kwargs.name === "Bo") {
                return [[5, "Bob"], [6, "Bobby"]];
            } else if (method === "name_search" && model === "partner" && kwargs.name === "Ali") {
                return [[9, "Alice"], [10, "Alicia"]];
            }

        }

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
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

        let items = target.querySelectorAll('.o_searchview_input_container li');
        assert.strictEqual(items.length, 6);
        assert.strictEqual(items[1].innerText, 'My Partner (Bar 1)');
        assert.strictEqual(items[3].innerText, 'My Selection (Bar 1)');
        assert.strictEqual(items[5].innerText, 'My Text (Bar 2)');

        // click again on the expand icon to hide the properties
        await click(target.querySelector(".o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 1, "Should have hidden the properties");

        // search for a partner, and expand the many2many property
        await editSearch(target, "Bo");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector("li:nth-child(3) .o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 8);
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
        assert.strictEqual(items.length, 6, "Should have folded the properties");
        assert.strictEqual(items[2].innerText, "My Partners (Bar 1)");
        assert.strictEqual(items[3].innerText, "My Selection (Bar 1)");

        // select Bobby
        await click(target.querySelector("li:nth-child(3) .o_expand"));
        await click(target.querySelector(".o_searchview_input_container li:nth-child(5)"));
        assert.deepEqual(getDomain(controlPanel), [["properties.my_partners", "in", 6]]);

        // expand the selection properties
        await click(target.querySelector(".o_control_panel"));
        await editSearch(target, "a");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector("li:nth-child(4) .o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 8, "Should have unfolded the selection properties");
        assert.strictEqual(items[4].innerText, "A");
        assert.strictEqual(items[5].innerText, "AA");

        // select the selection option "AA"
        await click(target.querySelector(".o_searchview_input_container li:nth-child(6)"));
        let expectedDomain = ["&", ["properties.my_partners", "in", 6], ["properties.my_selection", "=", "aa"]];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);

        // select the selection option "A"
        await click(target.querySelector(".o_control_panel"));
        await editSearch(target, "a");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector("li:nth-child(4) .o_expand"));
        await click(target.querySelector(".o_searchview_input_container li:nth-child(5)"));
        expectedDomain = [
            "&",
                ["properties.my_partners", "in", 6],
            "|",
                ["properties.my_selection", "=", "aa"],
                ["properties.my_selection", "=", "a"],
        ];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);

        // reset the search
        await click(target.querySelector('.o_facet_remove'));
        await click(target.querySelector('.o_facet_remove'));

        // search a many2one value
        await click(target.querySelector(".o_control_panel"));
        await editSearch(target, "Ali");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector("li:nth-child(2) .o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 8, "Should show the search result");
        assert.strictEqual(items[2].innerText, "Alice");
        assert.strictEqual(items[3].innerText, "Alicia");
        await click(target.querySelector(".o_searchview_input_container li:nth-child(4)"));
        expectedDomain = [["properties.my_partner", "=", 10]];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);

        // search a tag value
        await click(target.querySelector(".o_control_panel"));
        await editSearch(target, "A");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector("li:nth-child(5) .o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 8, "Should show the search result");
        assert.strictEqual(items[5].innerText, "A");
        assert.strictEqual(items[6].innerText, "AA");
        await click(target.querySelector(".o_searchview_input_container li:nth-child(7)"));
        expectedDomain = ["&", ["properties.my_partner", "=", 10], ["properties.my_tags", "in", "aa"]];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);
        // add the tab "B"
        await click(target.querySelector(".o_control_panel"));
        await editSearch(target, "B");
        await click(target.querySelector(".o_expand"));
        await click(target.querySelector("li:nth-child(5) .o_expand"));
        items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 7, "Should show the search result");
        assert.strictEqual(items[5].innerText, "B");
        await click(target.querySelector(".o_searchview_input_container li:nth-child(6)"));
        expectedDomain = [
            "&",
                ["properties.my_partner", "=", 10],
            "|",
                ["properties.my_tags", "in", "aa"],
                ["properties.my_tags", "in", "b"]];
        assert.deepEqual(getDomain(controlPanel), expectedDomain);
    });

    QUnit.test("search a property: definition record id in the context", async function (assert) {
        assert.expect(3);

        async function mockRPC(route, { method, model, args, kwargs }) {
            if (method === "search_read" && model === "partner"
                && args[1][0] === "display_name" && args[1][1] === "child_properties") {

                assert.deepEqual(args[0], [["id", "=", 2]],
                    "Should search only the active parent properties");

                const definition2 = [{
                    'type': 'char',
                    'string': 'My Text',
                    'name': 'my_text',
                }];

                return [
                    {'id': 2, 'display_name': 'Bar 2', 'child_properties': definition2},
                ];
            }
        }

        await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
            searchMenuTypes: [],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="properties"/>
                    </search>
                `,
            mockRPC,
            context: {active_id: 2},
        });

        await click(target.querySelector(".o_control_panel"));
        await editSearch(target, "a");
        await click(target.querySelector(".o_expand"));

        const items = target.querySelectorAll(".o_searchview_input_container li");
        assert.strictEqual(items.length, 2, "Should show the search result");
        assert.strictEqual(items[1].innerText, "My Text (Bar 2)");
    });
});
