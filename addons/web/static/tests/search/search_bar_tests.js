/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { click, makeDeferred, nextTick, patchWithCleanup, triggerEvent } from "../helpers/utils";
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
    });

    QUnit.module("SearchBar");

    QUnit.test("basic rendering", async function (assert) {
        assert.expect(1);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
            searchMenuTypes: [],
            searchViewId: false,
        });

        assert.strictEqual(
            document.activeElement,
            controlPanel.el.querySelector(".o_searchview input"),
            "searchview input should be focused"
        );
    });

    QUnit.test("navigation with facets", async function (assert) {
        assert.expect(4);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            context: { search_default_date_group_by: 1 },
        });

        assert.containsOnce(
            controlPanel,
            ".o_searchview .o_searchview_facet",
            "there should be one facet"
        );
        assert.strictEqual(
            document.activeElement,
            controlPanel.el.querySelector(".o_searchview input")
        );

        // press left to focus the facet
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowLeft" });
        assert.strictEqual(
            document.activeElement,
            controlPanel.el.querySelector(".o_searchview .o_searchview_facet")
        );

        // press right to focus the input
        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowRight" });
        assert.strictEqual(
            document.activeElement,
            controlPanel.el.querySelector(".o_searchview input")
        );
    });

    QUnit.test("search date and datetime fields. Support of timezones", async function (assert) {
        assert.expect(4);

        const originalZoneName = luxon.Settings.defaultZoneName;
        luxon.Settings.defaultZoneName = new luxon.FixedOffsetZone.instance(360);
        registerCleanup(() => {
            luxon.Settings.defaultZoneName = originalZoneName;
        });

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
            searchMenuTypes: [],
            searchViewId: false,
        });

        // Date case
        await editSearch(controlPanel, "07/15/1983");
        let searchInput = controlPanel.el.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" }); // select

        assert.deepEqual(
            getFacetTexts(controlPanel).map((str) => str.replace(/\s+/, " ")),
            ["Birthday 07/15/1983"],
            "The format of the date in the facet should be in locale"
        );

        assert.deepEqual(getDomain(controlPanel), [["birthday", "=", "1983-07-15"]]);

        // Close Facet
        await click(controlPanel.el.querySelector(".o_searchview_facet .o_facet_remove"));

        // DateTime case
        await editSearch(controlPanel, "07/15/1983 00:00:00");
        searchInput = controlPanel.el.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" }); // select

        assert.deepEqual(
            getFacetTexts(controlPanel).map((str) => str.replace(/\s+/, " ")),
            ["Birth DateTime\n07/15/1983 00:00:00"],
            "The format of the datetime in the facet should be in locale"
        );

        assert.deepEqual(getDomain(controlPanel), [["birth_datetime", "=", "1983-07-14 18:00:00"]]);
    });

    QUnit.test("autocomplete menu clickout interactions", async function (assert) {
        assert.expect(9);

        const controlPanel = await makeWithSearch({
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

        const input = controlPanel.el.querySelector(".o_searchview input");

        assert.containsNone(controlPanel, ".o_searchview_autocomplete");

        await editSearch(controlPanel, "Hello there");

        assert.strictEqual(input.value, "Hello there", "input value should be updated");
        assert.containsOnce(controlPanel, ".o_searchview_autocomplete");

        await triggerEvent(input, null, "keydown", { key: "Escape" });

        assert.strictEqual(input.value, "", "input value should be empty");
        assert.containsNone(controlPanel, ".o_searchview_autocomplete");

        await editSearch(controlPanel, "General Kenobi");

        assert.strictEqual(input.value, "General Kenobi", "input value should be updated");
        assert.containsOnce(controlPanel, ".o_searchview_autocomplete");

        await click(document.body);

        assert.strictEqual(input.value, "", "input value should be empty");
        assert.containsNone(controlPanel, ".o_searchview_autocomplete");
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

        await editSearch(controlPanel, "a");
        assert.containsN(
            controlPanel,
            ".o_searchview_autocomplete li",
            2,
            "there should be 2 result for 'a' in search bar autocomplete"
        );

        const searchInput = controlPanel.el.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });
        assert.strictEqual(
            controlPanel.el
                .querySelector(".o_searchview_input_container .o_facet_values")
                .innerText.trim(),
            "a",
            "There should be a field facet with label 'a'"
        );

        assert.deepEqual(getDomain(controlPanel), [["foo", "ilike", "a"]]);
    });

    QUnit.test("select an autocomplete field with `context` key", async function (assert) {
        assert.expect(8);

        let updateCount = 0;
        patchWithCleanup(ControlPanel.prototype, {
            async willUpdateProps() {
                updateCount++;
                await this._super(...arguments);
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
        await editSearch(controlPanel, "record");
        const searchInput = controlPanel.el.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowRight" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });

        assert.deepEqual(
            getFacetTexts(controlPanel).map((str) => str.replace(/\s+/, "")),
            ["BarFirst record"]
        );

        assert.strictEqual(updateCount, 1);

        assert.deepEqual(getDomain(controlPanel), [["bar", "=", 1]]);
        assert.deepEqual(controlPanel.env.searchModel.context.bar, [1]);

        // 'r' key to filter on bar "Second Record"
        await editSearch(controlPanel, "record");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowRight" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });

        assert.deepEqual(
            getFacetTexts(controlPanel).map((str) => str.replace(/\s+/, "")),
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
            async willUpdateProps() {
                updateCount++;
                await this._super(...arguments);
            },
        });

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
            searchMenuTypes: [],
            searchViewId: false,
        });

        const searchInput = controlPanel.el.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });

        assert.containsNone(controlPanel, ".o_searchview_facet_label");
        assert.strictEqual(updateCount, 1, "should have been updated once");
    });

    QUnit.test("selecting (no result) triggers a search bar rendering", async function (assert) {
        assert.expect(3);

        const controlPanel = await makeWithSearch({
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

        await editSearch(controlPanel, "hello there");

        // 'a' key to filter nothing on bar
        const searchInput = controlPanel.el.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowRight" });
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });

        assert.strictEqual(
            controlPanel.el
                .querySelector(".o_searchview_autocomplete .o_selection_focus")
                .innerText.trim(),
            "(no result)",
            "there should be no result for 'a' in bar"
        );

        await triggerEvent(searchInput, null, "keydown", { key: "Enter" });

        assert.containsNone(controlPanel, ".o_searchview_facet_label");
        assert.strictEqual(
            controlPanel.el.querySelector(".o_searchview input").value,
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
            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "partner",
                Component: ControlPanel,
                searchMenuTypes: [],
                searchViewId: false,
            });

            const searchInput = controlPanel.el.querySelector(".o_searchview input");

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
                controlPanel.el,
                ".o_searchview_autocomplete",
                "should display autocomplete dropdown menu on typing something in search view"
            );
            assert.strictEqual(
                controlPanel.el.querySelector(".o_searchview_autocomplete li").innerText.trim(),
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
                controlPanel.el.querySelector(".o_searchview_autocomplete li").innerText.trim(),
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
                controlPanel.el.querySelector(".o_searchview_autocomplete li").innerText.trim(),
                "Search Foo for: TEST",
                `1st filter suggestion should finally be updated with click selection on word "TEST" from IME`
            );
        }
    );

    QUnit.test("open search view autocomplete on paste value using mouse", async function (assert) {
        assert.expect(1);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "partner",
            Component: ControlPanel,
            searchMenuTypes: [],
            searchViewId: false,
        });

        // Simulate paste text through the mouse.
        const searchInput = controlPanel.el.querySelector(".o_searchview input");
        searchInput.value = "ABC";
        await triggerEvent(searchInput, null, "input", { inputType: "insertFromPaste" });
        assert.containsOnce(
            controlPanel,
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

        await editSearch(controlPanel, "rec");
        await click(controlPanel.el.querySelector(".o_searchview_autocomplete li:last-child"));

        assert.deepEqual(getDomain(controlPanel), [["bar", "child_of", "rec"]]);

        await removeFacet(controlPanel);

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(controlPanel, "rec");
        await click(controlPanel.el.querySelector(".o_expand"));
        await click(
            controlPanel.el.querySelector(".o_searchview_autocomplete li.o_menu_item.o_indent")
        );

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

        await editSearch(controlPanel, "null");

        assert.strictEqual(
            controlPanel.el.querySelector(".o_searchview_autocomplete .o_selection_focus")
                .innerText,
            "Search Foo for: null"
        );

        await click(
            controlPanel.el.querySelector(".o_searchview_autocomplete li.o_selection_focus a")
        );

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

        await editSearch(controlPanel, "y");

        assert.containsN(controlPanel, ".o_searchview_autocomplete li", 1);
        assert.strictEqual(
            controlPanel.el.querySelector(".o_searchview_autocomplete li:last-child").innerText,
            "Search Bool for: Yes"
        );

        // select "Yes"
        await click(controlPanel.el.querySelector(".o_searchview_autocomplete li:last-child"));

        assert.deepEqual(getDomain(controlPanel), [["bool", "=", true]]);

        await removeFacet(controlPanel);

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(controlPanel, "No");

        assert.containsN(controlPanel, ".o_searchview_autocomplete li", 1);
        assert.strictEqual(
            controlPanel.el.querySelector(".o_searchview_autocomplete li:last-child").innerText,
            "Search Bool for: No"
        );

        // select "No"
        await click(controlPanel.el.querySelector(".o_searchview_autocomplete li:last-child"));

        assert.deepEqual(getDomain(controlPanel), [["bool", "=", false]]);
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

        await editSearch(controlPanel, "ref");
        await validateSearch(controlPanel);

        assert.deepEqual(getDomain(controlPanel), [["ref", "ilike", "ref"]]);

        await removeFacet(controlPanel);

        assert.deepEqual(getDomain(controlPanel), []);

        await editSearch(controlPanel, "ref002");
        await validateSearch(controlPanel);

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
            const controlPanel = await makeWithSearch({
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
            await editSearch(controlPanel, "rec");
            await click(controlPanel.el.querySelector(".o_expand"));
            await triggerEvent(
                controlPanel.el,
                ".o_searchview_autocomplete li.o_menu_item:first-child",
                "mousemove"
            );
            assert.containsNone(controlPanel, ".o_searchview_autocomplete li.o_menu_item.o_indent");

            def.resolve();
            await nextTick();
            assert.containsN(controlPanel, ".o_searchview_autocomplete li.o_menu_item.o_indent", 5);
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
            const controlPanel = await makeWithSearch({
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
            await editSearch(controlPanel, "rec");
            await click(controlPanel.el.querySelector(".o_expand"));
            const searchInput = controlPanel.el.querySelector(".o_searchview input");
            await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
            assert.containsNone(controlPanel, ".o_searchview_autocomplete li.o_menu_item.o_indent");

            def.resolve();
            await nextTick();
            assert.containsN(controlPanel, ".o_searchview_autocomplete li.o_menu_item.o_indent", 5);
        }
    );

    QUnit.test("checks that an arrowDown always selects an item", async function (assert) {
        assert.expect(1);

        const controlPanel = await makeWithSearch({
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
        await editSearch(controlPanel, "rec");
        await click(controlPanel.el.querySelector(".o_expand"));
        click(controlPanel.el.querySelector(".o_expand"));
        triggerEvent(
            controlPanel.el,
            ".o_searchview_autocomplete li.o_menu_item.o_indent:last-child",
            "mousemove"
        );
        const searchInput = controlPanel.el.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowDown" });
        assert.containsOnce(controlPanel, ".o_selection_focus");
    });

    QUnit.test("checks that an arrowUp always selects an item", async function (assert) {
        assert.expect(1);

        const controlPanel = await makeWithSearch({
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
        await editSearch(controlPanel, "rec");
        await click(controlPanel.el.querySelector(".o_expand"));
        click(controlPanel.el.querySelector(".o_expand"));
        triggerEvent(
            controlPanel.el,
            ".o_searchview_autocomplete li.o_menu_item.o_indent:last-child",
            "mousemove"
        );
        const searchInput = controlPanel.el.querySelector(".o_searchview input");
        await triggerEvent(searchInput, null, "keydown", { key: "ArrowUp" });
        assert.containsOnce(controlPanel, ".o_selection_focus");
    });
});
