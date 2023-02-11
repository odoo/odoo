/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patchWithCleanup } from "../helpers/utils";
import {
    applyGroup,
    getFacetTexts,
    isItemSelected,
    isOptionSelected,
    makeWithSearch,
    setupControlPanelServiceRegistry,
    toggleAddCustomGroup,
    toggleGroupByMenu,
    toggleMenuItem,
} from "./helpers";

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
    });

    QUnit.module("CustomGroupByItem");

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(5);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
        });

        await toggleGroupByMenu(controlPanel);

        const customGroupByItem = controlPanel.el.querySelector(".o_add_custom_group_menu");
        assert.strictEqual(customGroupByItem.innerText.trim(), "Add Custom Group");

        assert.containsOnce(customGroupByItem, "button.dropdown-toggle");
        assert.containsNone(customGroupByItem, ".dropdown-menu");

        await toggleAddCustomGroup(controlPanel);

        assert.containsOnce(customGroupByItem, ".dropdown-menu");

        assert.deepEqual(
            [...controlPanel.el.querySelectorAll(".o_add_custom_group_menu select option")].map(
                (el) => el.innerText
            ),
            ["Birthday", "Date", "Foo"]
        );
    });

    QUnit.test(
        'the ID field should not be proposed in "Add Custom Group" menu',
        async function (assert) {
            assert.expect(1);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewFields: {
                    foo: { string: "Foo", type: "char", store: true, sortable: true },
                    id: { sortable: true, string: "ID", type: "integer" },
                },
            });

            await toggleGroupByMenu(controlPanel);
            await toggleAddCustomGroup(controlPanel);

            assert.deepEqual(
                [
                    ...controlPanel.el.querySelectorAll(
                        ".o_add_custom_group_menu .dropdown-menu select option"
                    ),
                ].map((el) => el.innerText),
                ["Foo"]
            );
        }
    );

    QUnit.test(
        'add a date field in "Add Custom Group" activate a groupby with global default option "month"',
        async function (assert) {
            assert.expect(6);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewFields: {
                    date_field: { string: "Date", type: "date", store: true, sortable: true },
                    id: { sortable: true, string: "ID", type: "integer" },
                },
            });
            await toggleGroupByMenu(controlPanel);

            assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
            assert.containsNone(controlPanel, ".o_menu_item");

            await toggleAddCustomGroup(controlPanel);
            await applyGroup(controlPanel);

            assert.deepEqual(controlPanel.env.searchModel.groupBy, ["date_field:month"]);
            assert.deepEqual(getFacetTexts(controlPanel), ["Date: Month"]);
            assert.ok(isItemSelected(controlPanel, "Date"));

            await toggleMenuItem(controlPanel, "Date");

            assert.ok(isOptionSelected(controlPanel, "Date", "Month"));
        }
    );

    QUnit.test("click on add custom group toggle group selector", async function (assert) {
        assert.expect(4);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewFields: {
                date: { sortable: true, name: "date", string: "Super Date", type: "date" },
            },
        });

        await toggleGroupByMenu(controlPanel);

        const addCustomGroupMenu = controlPanel.el.querySelector(".o_add_custom_group_menu");

        assert.strictEqual(addCustomGroupMenu.innerText.trim(), "Add Custom Group");

        await toggleAddCustomGroup(controlPanel);

        // Single select node with a single option
        assert.containsOnce(controlPanel, ".o_add_custom_group_menu .dropdown-menu select");
        assert.strictEqual(
            controlPanel.el
                .querySelector(".o_add_custom_group_menu .dropdown-menu select option")
                .innerText.trim(),
            "Super Date"
        );

        // Button apply
        assert.containsOnce(controlPanel, ".o_add_custom_group_menu .dropdown-menu .btn");
    });

    QUnit.test(
        "select a field name in Add Custom Group menu properly trigger the corresponding field",
        async function (assert) {
            assert.expect(4);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["groupBy"],
                searchViewFields: {
                    candle_light: {
                        sortable: true,
                        string: "Candlelight",
                        type: "boolean",
                    },
                },
            });

            await toggleGroupByMenu(controlPanel);
            await toggleAddCustomGroup(controlPanel);
            await applyGroup(controlPanel);

            assert.containsOnce(controlPanel, ".o_group_by_menu .o_menu_item");
            assert.containsOnce(controlPanel, ".o_add_custom_group_menu .dropdown-toggle");
            assert.containsOnce(controlPanel, ".o_add_custom_group_menu .dropdown-menu");
            assert.deepEqual(getFacetTexts(controlPanel), ["Candlelight"]);
        }
    );
});
