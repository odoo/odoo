/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { getFixture, getNodesTextContent, patchWithCleanup } from "../helpers/utils";
import {
    getFacetTexts,
    isItemSelected,
    isOptionSelected,
    makeWithSearch,
    selectGroup,
    setupControlPanelServiceRegistry,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "./helpers";
import { SearchBar } from "@web/search/search_bar/search_bar";

let target;
let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        bar: { string: "Bar", type: "many2one", relation: "partner" },
                        birthday: { string: "Birthday", type: "date", store: true, sortable: true },
                        date_field: { string: "Date", type: "date", store: true, sortable: true },
                        float_field: { string: "Float", type: "float", group_operator: "sum" },
                        foo: { string: "Foo", type: "char", store: true, sortable: true },
                    },
                    records: {},
                },
            },
            views: {
                "foo,false,search": `<search/>`,
            },
        };
        setupControlPanelServiceRegistry();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
        target = getFixture();
    });

    QUnit.module("CustomGroupByItem");

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(2);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: SearchBar,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
        });

        await toggleSearchBarMenu(target);

        const groupByMenu = target.querySelector(".o_group_by_menu");
        assert.strictEqual(
            groupByMenu.querySelector(".o_group_by_menu option[disabled]").innerText.trim(),
            "Add Custom Group"
        );
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(".o_add_custom_group_menu option:not([disabled])")
            ),
            ["Birthday", "Date", "Foo"]
        );
    });

    QUnit.test(
        'the ID field should not be proposed in "Add Custom Group" menu',
        async function (assert) {
            assert.expect(1);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewFields: {
                    foo: { string: "Foo", type: "char", store: true, sortable: true },
                    id: { sortable: true, string: "ID", type: "integer" },
                },
            });

            await toggleSearchBarMenu(target);
            const optionDescriptions = [
                ...target.querySelectorAll(".o_add_custom_group_menu option:not([disabled])"),
            ].map((option) => option.innerText.trim());
            assert.deepEqual(optionDescriptions, ["Foo"]);
        }
    );

    QUnit.test(
        'stored many2many should be proposed in "Add Custom Group" menu',
        async function (assert) {
            assert.expect(1);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewFields: {
                    char_a: { string: "Char A", type: "char", store: true, sortable: true },
                    m2m_no_stored: { string: "M2M Not Stored", type: "many2many" },
                    m2m_stored: {
                        string: "M2M Stored",
                        type: "many2many",
                        store: true,
                    },
                },
            });

            await toggleSearchBarMenu(target);
            const optionDescriptions = [
                ...target.querySelectorAll(".o_add_custom_group_menu option:not([disabled])"),
            ].map((option) => option.innerText.trim());
            assert.deepEqual(optionDescriptions, ["Char A", "M2M Stored"]);
        }
    );

    QUnit.test(
        'add a date field in "Add Custom Group" activate a groupby with global default option "month"',
        async function (assert) {
            assert.expect(6);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewFields: {
                    date_field: { string: "Date", type: "date", store: true, sortable: true },
                    id: { sortable: true, string: "ID", type: "integer" },
                },
            });
            await toggleSearchBarMenu(target);

            assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
            assert.containsOnce(target, ".o_add_custom_group_menu"); //Add Custom Group

            await selectGroup(target, "date_field");

            assert.deepEqual(controlPanel.env.searchModel.groupBy, ["date_field:month"]);
            assert.deepEqual(getFacetTexts(target), ["Date: Month"]);
            assert.ok(isItemSelected(target, "Date"));

            await toggleMenuItem(target, "Date");

            assert.ok(isOptionSelected(target, "Date", "Month"));
        }
    );

    QUnit.test("click on add custom group toggle group selector", async function (assert) {
        assert.expect(3);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: SearchBar,
            searchMenuTypes: ["groupBy"],
            searchViewFields: {
                date: { sortable: true, name: "date", string: "Super Date", type: "date" },
            },
        });

        await toggleSearchBarMenu(target);

        const addCustomGroupMenu = target.querySelector(".o_add_custom_group_menu");

        assert.strictEqual(
            addCustomGroupMenu.querySelector("option[disabled]").innerText.trim(),
            "Add Custom Group"
        );

        // Single select node with a single option
        assert.containsOnce(target, ".o_add_custom_group_menu option:not([disabled])");
        assert.deepEqual(
            target.querySelector(".o_add_custom_group_menu option:not([disabled])").textContent,
            "Super Date"
        );
    });

    QUnit.test(
        "select a field name in Add Custom Group menu properly trigger the corresponding field",
        async function (assert) {
            assert.expect(3);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewFields: {
                    candle_light: {
                        sortable: true,
                        string: "Candlelight",
                        type: "boolean",
                    },
                },
            });

            await toggleSearchBarMenu(target);
            await selectGroup(target, "candle_light");

            assert.containsN(target, ".o_group_by_menu .o_menu_item", 2);
            assert.containsOnce(target, ".o_add_custom_group_menu");
            assert.deepEqual(getFacetTexts(target), ["Candlelight"]);
        }
    );
});
