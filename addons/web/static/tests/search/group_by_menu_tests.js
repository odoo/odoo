/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patchWithCleanup } from "../helpers/utils";
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

    QUnit.module("GroupByMenu");

    QUnit.test(
        "simple rendering with neither groupbys nor groupable fields",
        async function (assert) {
            assert.expect(3);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewFields: {},
            });

            await toggleGroupByMenu(controlPanel);

            assert.containsNone(controlPanel, ".o_menu_item");
            assert.containsNone(controlPanel, ".dropdown-divider");
            assert.containsNone(controlPanel, ".o_add_custom_group_menu");
        }
    );

    QUnit.test("simple rendering with no groupby", async function (assert) {
        assert.expect(3);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["groupBy"],
            searchViewId: false,
        });

        await toggleGroupByMenu(controlPanel);

        assert.containsNone(controlPanel, ".o_menu_item");
        assert.containsNone(controlPanel, ".dropdown-divider");
        assert.containsOnce(controlPanel, ".o_add_custom_group_menu");
    });

    QUnit.test("simple rendering with a single groupby", async function (assert) {
        assert.expect(4);

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

        await toggleGroupByMenu(controlPanel);

        assert.containsOnce(controlPanel, ".o_menu_item");
        assert.strictEqual(controlPanel.el.querySelector(".o_menu_item").innerText.trim(), "Foo");
        assert.containsOnce(controlPanel, ".dropdown-divider");
        assert.containsOnce(controlPanel, ".o_add_custom_group_menu");
    });

    QUnit.test('toggle a "simple" groupby in groupby menu works', async function (assert) {
        assert.expect(10);

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

        await toggleGroupByMenu(controlPanel);

        assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
        assert.deepEqual(getFacetTexts(controlPanel), []);
        assert.notOk(isItemSelected(controlPanel, "Foo"));

        await toggleMenuItem(controlPanel, "Foo");

        assert.deepEqual(controlPanel.env.searchModel.groupBy, ["foo"]);
        assert.deepEqual(getFacetTexts(controlPanel), ["Foo"]);
        assert.containsOnce(
            controlPanel.el.querySelector(".o_searchview .o_searchview_facet"),
            "span.fa.fa-bars.o_searchview_facet_label"
        );
        assert.ok(isItemSelected(controlPanel, "Foo"));

        await toggleMenuItem(controlPanel, "Foo");

        assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
        assert.deepEqual(getFacetTexts(controlPanel), []);
        assert.notOk(isItemSelected(controlPanel, "Foo"));
    });

    QUnit.test('toggle a "simple" groupby quickly does not crash', async function (assert) {
        assert.expect(1);

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

        await toggleGroupByMenu(controlPanel);

        toggleMenuItem(controlPanel, "Foo");
        toggleMenuItem(controlPanel, "Foo");

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

            await toggleGroupByMenu(controlPanel);

            assert.deepEqual(getFacetTexts(controlPanel), ["Foo"]);
            assert.deepEqual(controlPanel.env.searchModel.groupBy, ["foo"]);
            assert.ok(isItemSelected(controlPanel, "Foo"));

            await removeFacet(controlPanel, "Foo");

            assert.deepEqual(getFacetTexts(controlPanel), []);
            assert.deepEqual(controlPanel.env.searchModel.groupBy, []);

            await toggleGroupByMenu(controlPanel);

            assert.notOk(isItemSelected(controlPanel, "Foo"));
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

        await toggleGroupByMenu(controlPanel);

        assert.deepEqual(controlPanel.env.searchModel.groupBy, ["date_field:week"]);

        await toggleMenuItem(controlPanel, "Date");

        assert.ok(isOptionSelected(controlPanel, "Date", "Week"));

        assert.deepEqual(
            [...controlPanel.el.querySelectorAll(".o_item_option")].map((el) => el.innerText),
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
            await toggleMenuItemOption(controlPanel, "Date", s.description);

            assert.deepEqual(controlPanel.env.searchModel.groupBy, s.groupBy);
            assert.deepEqual(getFacetTexts(controlPanel), s.facetTexts);
            s.selectedoptions.forEach((description) => {
                assert.ok(isOptionSelected(controlPanel, "Date", description));
            });
        }
    });

    QUnit.test("interval options are correctly grouped and ordered", async function (assert) {
        assert.expect(8);

        const controlPanel = await makeWithSearch({
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

        assert.deepEqual(getFacetTexts(controlPanel), ["Bar"]);

        // open menu 'Group By'
        await toggleGroupByMenu(controlPanel);

        // Open the groupby 'Date'
        await toggleMenuItem(controlPanel, "Date");
        // select option 'week'
        await toggleMenuItemOption(controlPanel, "Date", "Week");

        assert.deepEqual(getFacetTexts(controlPanel), ["Bar>Date: Week"]);

        // select option 'day'
        await toggleMenuItemOption(controlPanel, "Date", "Day");

        assert.deepEqual(getFacetTexts(controlPanel), ["Bar>Date: Week>Date: Day"]);

        // select option 'year'
        await toggleMenuItemOption(controlPanel, "Date", "Year");

        assert.deepEqual(getFacetTexts(controlPanel), ["Bar>Date: Year>Date: Week>Date: Day"]);

        // select 'Foo'
        await toggleMenuItem(controlPanel, "Foo");

        assert.deepEqual(getFacetTexts(controlPanel), ["Bar>Date: Year>Date: Week>Date: Day>Foo"]);

        // select option 'quarter'
        await toggleMenuItem(controlPanel, "Date");
        await toggleMenuItemOption(controlPanel, "Date", "Quarter");

        assert.deepEqual(getFacetTexts(controlPanel), [
            "Bar>Date: Year>Date: Quarter>Date: Week>Date: Day>Foo",
        ]);

        // unselect 'Bar'
        await toggleMenuItem(controlPanel, "Bar");

        assert.deepEqual(getFacetTexts(controlPanel), [
            "Date: Year>Date: Quarter>Date: Week>Date: Day>Foo",
        ]);

        // unselect option 'week'
        await toggleMenuItem(controlPanel, "Date");
        await toggleMenuItemOption(controlPanel, "Date", "Week");

        assert.deepEqual(getFacetTexts(controlPanel), ["Date: Year>Date: Quarter>Date: Day>Foo"]);
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
        assert.deepEqual(getFacetTexts(controlPanel), ["Date: Week>Birthday: Month"]);
    });

    QUnit.test("a separator in groupbys does not cause problems", async function (assert) {
        assert.expect(23);

        const controlPanel = await makeWithSearch({
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

        await toggleGroupByMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Date");
        await toggleMenuItemOption(controlPanel, "Date", "Day");

        assert.ok(isItemSelected(controlPanel, "Date"));
        assert.notOk(isItemSelected(controlPanel, "Bar"));
        assert.ok(isOptionSelected(controlPanel, "Date", "Day"), "selected");
        assert.deepEqual(getFacetTexts(controlPanel), ["Date: Day"]);

        await toggleMenuItem(controlPanel, "Bar");
        await toggleMenuItem(controlPanel, "Date");

        assert.ok(isItemSelected(controlPanel, "Date"));
        assert.ok(isItemSelected(controlPanel, "Bar"));
        assert.ok(isOptionSelected(controlPanel, "Date", "Day"), "selected");
        assert.deepEqual(getFacetTexts(controlPanel), ["Date: Day>Bar"]);

        await toggleMenuItemOption(controlPanel, "Date", "Quarter");

        assert.ok(isItemSelected(controlPanel, "Date"));
        assert.ok(isItemSelected(controlPanel, "Bar"));
        assert.ok(isOptionSelected(controlPanel, "Date", "Quarter"), "selected");
        assert.ok(isOptionSelected(controlPanel, "Date", "Day"), "selected");
        assert.deepEqual(getFacetTexts(controlPanel), ["Date: Quarter>Date: Day>Bar"]);

        await toggleMenuItem(controlPanel, "Bar");
        await toggleMenuItem(controlPanel, "Date");

        assert.ok(isItemSelected(controlPanel, "Date"));
        assert.notOk(isItemSelected(controlPanel, "Bar"));
        assert.ok(isOptionSelected(controlPanel, "Date", "Quarter"), "selected");
        assert.ok(isOptionSelected(controlPanel, "Date", "Day"), "selected");
        assert.deepEqual(getFacetTexts(controlPanel), ["Date: Quarter>Date: Day"]);

        await removeFacet(controlPanel);

        assert.deepEqual(getFacetTexts(controlPanel), []);

        await toggleGroupByMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Date");

        assert.notOk(isItemSelected(controlPanel, "Date"));
        assert.notOk(isItemSelected(controlPanel, "Bar"));
        assert.notOk(isOptionSelected(controlPanel, "Date", "Quarter"), "selected");
        assert.notOk(isOptionSelected(controlPanel, "Date", "Day"), "selected");
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
        assert.deepEqual(getFacetTexts(controlPanel), []);
    });
});
