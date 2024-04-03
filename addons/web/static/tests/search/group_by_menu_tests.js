/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { getFixture, patchWithCleanup } from "../helpers/utils";
import {
    getFacetTexts,
    isItemSelected,
    isOptionSelected,
    makeWithSearch,
    removeFacet,
    setupControlPanelServiceRegistry,
    toggleGroupByMenu,
    toggleMenuItem,
    toggleMenuItemOption,
} from "./helpers";

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

    QUnit.module("GroupByMenu");

    QUnit.test(
        "simple rendering with neither groupbys nor groupable fields",
        async function (assert) {
            assert.expect(3);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewFields: {},
            });

            await toggleGroupByMenu(target);

            assert.containsNone(target, ".o_menu_item");
            assert.containsNone(target, ".dropdown-divider");
            assert.containsNone(target, ".o_add_custom_group_menu");
        }
    );

    QUnit.test("simple rendering with no groupby", async function (assert) {
        assert.expect(3);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
        });

        await toggleGroupByMenu(target);

        assert.containsNone(target, ".o_menu_item");
        assert.containsNone(target, ".dropdown-divider");
        assert.containsOnce(target, ".o_add_custom_group_menu");
    });

    QUnit.test("simple rendering with a single groupby", async function (assert) {
        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
        });

        await toggleGroupByMenu(target);

        assert.containsOnce(target, ".o_menu_item");
        const menuItem = target.querySelector(".o_menu_item");
        assert.strictEqual(menuItem.innerText.trim(), "Foo");
        assert.strictEqual(menuItem.getAttribute("role"), "menuitemcheckbox");
        assert.strictEqual(menuItem.ariaChecked, "false");
        assert.containsOnce(target, ".dropdown-divider");
        assert.containsOnce(target, ".o_add_custom_group_menu");
    });

    QUnit.test('toggle a "simple" groupby in groupby menu works', async function (assert) {
        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
        });

        await toggleGroupByMenu(target);

        assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
        assert.deepEqual(getFacetTexts(target), []);
        assert.notOk(isItemSelected(target, "Foo"));
        const menuItem = target.querySelector(".o_menu_item");
        assert.strictEqual(menuItem.innerText.trim(), "Foo");
        assert.strictEqual(menuItem.getAttribute("role"), "menuitemcheckbox");
        assert.strictEqual(menuItem.ariaChecked, "false");
        await toggleMenuItem(target, "Foo");
        assert.strictEqual(menuItem.ariaChecked, "true");

        assert.deepEqual(controlPanel.env.searchModel.groupBy, ["foo"]);
        assert.deepEqual(getFacetTexts(target), ["Foo"]);
        assert.containsOnce(
            target.querySelector(".o_searchview .o_searchview_facet"),
            "span.oi.oi-group.o_searchview_facet_label"
        );
        assert.ok(isItemSelected(target, "Foo"));

        await toggleMenuItem(target, "Foo");

        assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
        assert.deepEqual(getFacetTexts(target), []);
        assert.notOk(isItemSelected(target, "Foo"));
    });

    QUnit.test('toggle a "simple" groupby quickly does not crash', async function (assert) {
        assert.expect(1);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
        });

        await toggleGroupByMenu(target);

        toggleMenuItem(target, "Foo");
        toggleMenuItem(target, "Foo");

        assert.ok(true);
    });

    QUnit.test(
        'remove a "Group By" facet properly unchecks groupbys in groupby menu',
        async function (assert) {
            assert.expect(6);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                context: { search_default_group_by_foo: 1 },
            });

            await toggleGroupByMenu(target);

            assert.deepEqual(getFacetTexts(target), ["Foo"]);
            assert.deepEqual(controlPanel.env.searchModel.groupBy, ["foo"]);
            assert.ok(isItemSelected(target, "Foo"));

            await removeFacet(target, "Foo");

            assert.deepEqual(getFacetTexts(target), []);
            assert.deepEqual(controlPanel.env.searchModel.groupBy, []);

            await toggleGroupByMenu(target);

            assert.notOk(isItemSelected(target, "Foo"));
        }
    );

    QUnit.test("group by a date field using interval works", async function (assert) {
        assert.expect(21);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <filter string="Date" name="date" context="{'group_by': 'date_field:week'}"/>
                    </search>
                `,
            context: { search_default_date: 1 },
        });

        await toggleGroupByMenu(target);

        assert.deepEqual(controlPanel.env.searchModel.groupBy, ["date_field:week"]);

        await toggleMenuItem(target, "Date");

        assert.ok(isOptionSelected(target, "Date", "Week"));

        assert.deepEqual(
            [...target.querySelectorAll(".o_item_option")].map((el) => el.innerText),
            ["Year", "Quarter", "Month", "Week", "Day"]
        );

        const steps = [
            {
                description: "Year",
                facetTexts: ["Date: Year>Date: Week"],
                selectedoptions: ["Year", "Week"],
                groupBy: ["date_field:year", "date_field:week"],
            },
            {
                description: "Month",
                facetTexts: ["Date: Year>Date: Month>Date: Week"],
                selectedoptions: ["Year", "Month", "Week"],
                groupBy: ["date_field:year", "date_field:month", "date_field:week"],
            },
            {
                description: "Week",
                facetTexts: ["Date: Year>Date: Month"],
                selectedoptions: ["Year", "Month"],
                groupBy: ["date_field:year", "date_field:month"],
            },
            {
                description: "Month",
                facetTexts: ["Date: Year"],
                selectedoptions: ["Year"],
                groupBy: ["date_field:year"],
            },
            { description: "Year", facetTexts: [], selectedoptions: [], groupBy: [] },
        ];
        for (const s of steps) {
            await toggleMenuItemOption(target, "Date", s.description);

            assert.deepEqual(controlPanel.env.searchModel.groupBy, s.groupBy);
            assert.deepEqual(getFacetTexts(target), s.facetTexts);
            s.selectedoptions.forEach((description) => {
                assert.ok(isOptionSelected(target, "Date", description));
            });
        }
    });

    QUnit.test("interval options are correctly grouped and ordered", async function (assert) {
        assert.expect(8);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <filter string="Bar" name="bar" context="{'group_by': 'bar'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'date_field'}"/>
                        <filter string="Foo" name="foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
            context: { search_default_bar: 1 },
        });

        assert.deepEqual(getFacetTexts(target), ["Bar"]);

        // open menu 'Group By'
        await toggleGroupByMenu(target);

        // Open the groupby 'Date'
        await toggleMenuItem(target, "Date");
        // select option 'week'
        await toggleMenuItemOption(target, "Date", "Week");

        assert.deepEqual(getFacetTexts(target), ["Bar>Date: Week"]);

        // select option 'day'
        await toggleMenuItemOption(target, "Date", "Day");

        assert.deepEqual(getFacetTexts(target), ["Bar>Date: Week>Date: Day"]);

        // select option 'year'
        await toggleMenuItemOption(target, "Date", "Year");

        assert.deepEqual(getFacetTexts(target), ["Bar>Date: Year>Date: Week>Date: Day"]);

        // select 'Foo'
        await toggleMenuItem(target, "Foo");

        assert.deepEqual(getFacetTexts(target), ["Bar>Date: Year>Date: Week>Date: Day>Foo"]);

        // select option 'quarter'
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "Quarter");

        assert.deepEqual(getFacetTexts(target), [
            "Bar>Date: Year>Date: Quarter>Date: Week>Date: Day>Foo",
        ]);

        // unselect 'Bar'
        await toggleMenuItem(target, "Bar");

        assert.deepEqual(getFacetTexts(target), [
            "Date: Year>Date: Quarter>Date: Week>Date: Day>Foo",
        ]);

        // unselect option 'week'
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "Week");

        assert.deepEqual(getFacetTexts(target), ["Date: Year>Date: Quarter>Date: Day>Foo"]);
    });

    QUnit.test("default groupbys can be ordered", async function (assert) {
        assert.expect(2);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'date_field:week'}"/>
                    </search>
                `,
            context: { search_default_birthday: 2, search_default_date: 1 },
        });

        // the default groupbys should be activated in the right order
        assert.deepEqual(controlPanel.env.searchModel.groupBy, [
            "date_field:week",
            "birthday:month",
        ]);
        assert.deepEqual(getFacetTexts(target), ["Date: Week>Birthday: Month"]);
    });

    QUnit.test("a separator in groupbys does not cause problems", async function (assert) {
        assert.expect(23);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <filter string="Date" name="coolName" context="{'group_by': 'date_field'}"/>
                        <separator/>
                        <filter string="Bar" name="superName" context="{'group_by': 'bar'}"/>
                    </search>
                `,
        });

        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "Day");

        assert.ok(isItemSelected(target, "Date"));
        assert.notOk(isItemSelected(target, "Bar"));
        assert.ok(isOptionSelected(target, "Date", "Day"), "selected");
        assert.deepEqual(getFacetTexts(target), ["Date: Day"]);

        await toggleMenuItem(target, "Bar");
        await toggleMenuItem(target, "Date");

        assert.ok(isItemSelected(target, "Date"));
        assert.ok(isItemSelected(target, "Bar"));
        assert.ok(isOptionSelected(target, "Date", "Day"), "selected");
        assert.deepEqual(getFacetTexts(target), ["Date: Day>Bar"]);

        await toggleMenuItemOption(target, "Date", "Quarter");

        assert.ok(isItemSelected(target, "Date"));
        assert.ok(isItemSelected(target, "Bar"));
        assert.ok(isOptionSelected(target, "Date", "Quarter"), "selected");
        assert.ok(isOptionSelected(target, "Date", "Day"), "selected");
        assert.deepEqual(getFacetTexts(target), ["Date: Quarter>Date: Day>Bar"]);

        await toggleMenuItem(target, "Bar");
        await toggleMenuItem(target, "Date");

        assert.ok(isItemSelected(target, "Date"));
        assert.notOk(isItemSelected(target, "Bar"));
        assert.ok(isOptionSelected(target, "Date", "Quarter"), "selected");
        assert.ok(isOptionSelected(target, "Date", "Day"), "selected");
        assert.deepEqual(getFacetTexts(target), ["Date: Quarter>Date: Day"]);

        await removeFacet(target);

        assert.deepEqual(getFacetTexts(target), []);

        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Date");

        assert.notOk(isItemSelected(target, "Date"));
        assert.notOk(isItemSelected(target, "Bar"));
        assert.notOk(isOptionSelected(target, "Date", "Quarter"), "selected");
        assert.notOk(isOptionSelected(target, "Date", "Day"), "selected");
    });

    QUnit.test("falsy search default groupbys are not activated", async function (assert) {
        assert.expect(2);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
                    </search>
                `,
            context: { search_default_birthday: false, search_default_foo: 0 },
        });

        assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
        assert.deepEqual(getFacetTexts(target), []);
    });

    QUnit.test(
        "Custom group by menu is displayed when hideCustomGroupBy is not set",
        async function (assert) {
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                searchMenuTypes: ["groupBy"],
            });

            await toggleGroupByMenu(target);

            assert.containsOnce(target, ".o_add_custom_group_menu");
        }
    );

    QUnit.test(
        "Custom group by menu is displayed when hideCustomGroupBy is false",
        async function (assert) {
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                hideCustomGroupBy: false,
                searchMenuTypes: ["groupBy"],
            });

            await toggleGroupByMenu(target);

            assert.containsOnce(target, ".o_add_custom_group_menu");
        }
    );

    QUnit.test(
        "Custom group by menu is displayed when hideCustomGroupBy is true",
        async function (assert) {
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                hideCustomGroupBy: true,
                searchMenuTypes: ["groupBy"],
            });

            await toggleGroupByMenu(target);

            assert.containsNone(target, ".o_add_custom_group_menu");
        }
    );
});
