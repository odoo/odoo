/** @odoo-module **/

import { patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import {
    getFacetTexts,
    isItemSelected,
    isOptionSelected,
    makeWithSearch,
    setupControlPanelServiceRegistry,
    toggleFilterMenu,
    toggleMenuItem,
    toggleMenuItemOption,
} from "./helpers";

function getDomain(controlPanel) {
    return controlPanel.env.searchModel.domain;
}

function getContext(controlPanel) {
    return controlPanel.env.searchModel.context;
}

let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        date_field: {
                            string: "Date",
                            type: "date",
                            store: true,
                            sortable: true,
                            searchable: true,
                        },
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

    QUnit.module("FilterMenu");

    QUnit.test("simple rendering with no filter", async function (assert) {
        assert.expect(3);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(controlPanel);
        assert.containsNone(controlPanel, ".o_menu_item");
        assert.containsNone(controlPanel, ".dropdown-divider");
        assert.containsOnce(controlPanel, ".o_add_custom_filter_menu");
    });

    QUnit.test("simple rendering with a single filter", async function (assert) {
        assert.expect(3);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewArch: `
                    <search>
                        <filter string="Foo" name="foo" domain="[]"/>
                    </search>
                `,
        });

        await toggleFilterMenu(controlPanel);
        assert.containsOnce(controlPanel, ".o_menu_item");
        assert.containsOnce(controlPanel, ".dropdown-divider");
        assert.containsOnce(controlPanel, ".o_add_custom_filter_menu");
    });

    QUnit.test('toggle a "simple" filter in filter menu works', async function (assert) {
        assert.expect(10);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewArch: `
                    <search>
                        <filter string="Foo" name="foo" domain="[('foo', '=', 'qsdf')]"/>
                    </search>
                `,
        });

        await toggleFilterMenu(controlPanel);
        assert.deepEqual(getFacetTexts(controlPanel), []);
        assert.notOk(isItemSelected(controlPanel, "Foo"));
        assert.deepEqual(getDomain(controlPanel), []);

        await toggleMenuItem(controlPanel, "Foo");

        assert.deepEqual(getFacetTexts(controlPanel), ["Foo"]);
        assert.containsOnce(
            controlPanel.el.querySelector(".o_searchview .o_searchview_facet"),
            "span.fa.fa-filter.o_searchview_facet_label"
        );
        assert.ok(isItemSelected(controlPanel, "Foo"));
        assert.deepEqual(getDomain(controlPanel), [["foo", "=", "qsdf"]]);

        await toggleMenuItem(controlPanel, "Foo");

        assert.deepEqual(getFacetTexts(controlPanel), []);
        assert.notOk(isItemSelected(controlPanel, "Foo"));
        assert.deepEqual(getDomain(controlPanel), []);
    });

    QUnit.test("filter by a date field using period works", async function (assert) {
        assert.expect(57);

        patchDate(2017, 2, 22, 1, 0, 0);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewArch: `
                    <search>
                        <filter string="Date" name="date_field" date="date_field"/>
                    </search>
                `,
            context: { search_default_date_field: 1 },
        });

        await toggleFilterMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Date");

        const optionEls = controlPanel.el.querySelectorAll(".dropdown .o_item_option");

        // default filter should be activated with the global default period 'this_month'
        assert.deepEqual(getDomain(controlPanel), [
            "&",
            ["date_field", ">=", "2017-03-01"],
            ["date_field", "<=", "2017-03-31"],
        ]);
        assert.ok(isItemSelected(controlPanel, "Date"));
        assert.ok(isOptionSelected(controlPanel, "Date", "March"));

        // check option descriptions
        const optionDescriptions = [...optionEls].map((e) => e.innerText.trim());
        const expectedDescriptions = [
            "March",
            "February",
            "January",
            "Q4",
            "Q3",
            "Q2",
            "Q1",
            "2017",
            "2016",
            "2015",
        ];
        assert.deepEqual(optionDescriptions, expectedDescriptions);

        // check generated domains
        const steps = [
            {
                toggledOption: "March",
                resultingFacet: "Date: 2017",
                selectedoptions: ["2017"],
                domain: [
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-12-31"],
                ],
            },
            {
                toggledOption: "February",
                resultingFacet: "Date: February 2017",
                selectedoptions: ["February", "2017"],
                domain: [
                    "&",
                    ["date_field", ">=", "2017-02-01"],
                    ["date_field", "<=", "2017-02-28"],
                ],
            },
            {
                toggledOption: "February",
                resultingFacet: "Date: 2017",
                selectedoptions: ["2017"],
                domain: [
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-12-31"],
                ],
            },
            {
                toggledOption: "January",
                resultingFacet: "Date: January 2017",
                selectedoptions: ["January", "2017"],
                domain: [
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-01-31"],
                ],
            },
            {
                toggledOption: "Q4",
                resultingFacet: "Date: January 2017/Q4 2017",
                selectedoptions: ["January", "Q4", "2017"],
                domain: [
                    "|",
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-01-31"],
                    "&",
                    ["date_field", ">=", "2017-10-01"],
                    ["date_field", "<=", "2017-12-31"],
                ],
            },
            {
                toggledOption: "January",
                resultingFacet: "Date: Q4 2017",
                selectedoptions: ["Q4", "2017"],
                domain: [
                    "&",
                    ["date_field", ">=", "2017-10-01"],
                    ["date_field", "<=", "2017-12-31"],
                ],
            },
            {
                toggledOption: "Q4",
                resultingFacet: "Date: 2017",
                selectedoptions: ["2017"],
                domain: [
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-12-31"],
                ],
            },
            {
                toggledOption: "Q1",
                resultingFacet: "Date: Q1 2017",
                selectedoptions: ["Q1", "2017"],
                domain: [
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-03-31"],
                ],
            },
            {
                toggledOption: "Q1",
                resultingFacet: "Date: 2017",
                selectedoptions: ["2017"],
                domain: [
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-12-31"],
                ],
            },
            {
                toggledOption: "2017",
                selectedoptions: [],
                domain: [],
            },
            {
                toggledOption: "2017",
                resultingFacet: "Date: 2017",
                selectedoptions: ["2017"],
                domain: [
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-12-31"],
                ],
            },
            {
                toggledOption: "2016",
                resultingFacet: "Date: 2016/2017",
                selectedoptions: ["2017", "2016"],
                domain: [
                    "|",
                    "&",
                    ["date_field", ">=", "2016-01-01"],
                    ["date_field", "<=", "2016-12-31"],
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-12-31"],
                ],
            },
            {
                toggledOption: "2015",
                resultingFacet: "Date: 2015/2016/2017",
                selectedoptions: ["2017", "2016", "2015"],
                domain: [
                    "|",
                    "&",
                    ["date_field", ">=", "2015-01-01"],
                    ["date_field", "<=", "2015-12-31"],
                    "|",
                    "&",
                    ["date_field", ">=", "2016-01-01"],
                    ["date_field", "<=", "2016-12-31"],
                    "&",
                    ["date_field", ">=", "2017-01-01"],
                    ["date_field", "<=", "2017-12-31"],
                ],
            },
            {
                toggledOption: "March",
                resultingFacet: "Date: March 2015/March 2016/March 2017",
                selectedoptions: ["March", "2017", "2016", "2015"],
                domain: [
                    "|",
                    "&",
                    ["date_field", ">=", "2015-03-01"],
                    ["date_field", "<=", "2015-03-31"],
                    "|",
                    "&",
                    ["date_field", ">=", "2016-03-01"],
                    ["date_field", "<=", "2016-03-31"],
                    "&",
                    ["date_field", ">=", "2017-03-01"],
                    ["date_field", "<=", "2017-03-31"],
                ],
            },
        ];
        for (const s of steps) {
            await toggleMenuItemOption(controlPanel, "Date", s.toggledOption);
            assert.deepEqual(getDomain(controlPanel), s.domain);
            if (s.resultingFacet) {
                assert.deepEqual(getFacetTexts(controlPanel), [s.resultingFacet]);
            } else {
                assert.deepEqual(getFacetTexts(controlPanel), []);
            }
            s.selectedoptions.forEach((option) => {
                assert.ok(
                    isOptionSelected(controlPanel, "Date", option),
                    `at step ${steps.indexOf(s) + 1}, ${option} should be selected`
                );
            });
        }
    });

    QUnit.test(
        "filter by a date field using period works even in January",
        async function (assert) {
            assert.expect(5);

            patchDate(2017, 0, 7, 3, 0, 0);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewArch: `
                        <search>
                            <filter string="Date" name="some_filter" date="date_field" default_period="last_month"/>
                        </search>
                    `,
                context: { search_default_some_filter: 1 },
            });

            assert.deepEqual(getDomain(controlPanel), [
                "&",
                ["date_field", ">=", "2016-12-01"],
                ["date_field", "<=", "2016-12-31"],
            ]);

            assert.deepEqual(getFacetTexts(controlPanel), ["Date: December 2016"]);

            await toggleFilterMenu(controlPanel);
            await toggleMenuItem(controlPanel, "Date");

            assert.ok(isItemSelected(controlPanel, "Date"));
            assert.ok(isOptionSelected(controlPanel, "Date", "December"));
            assert.ok(isOptionSelected(controlPanel, "Date", "2016"));
        }
    );

    QUnit.test("`context` key in <filter> is used", async function (assert) {
        assert.expect(1);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewArch: `
                    <search>
                        <filter string="Filter" name="some_filter" domain="[]" context="{'coucou_1': 1}"/>
                    </search>
                `,
            context: { search_default_some_filter: 1 },
        });

        assert.deepEqual(getContext(controlPanel), {
            coucou_1: 1,
            lang: "en",
            tz: "taht",
            uid: 7,
        });
    });

    QUnit.test("Filter with JSON-parsable domain works", async function (assert) {
        assert.expect(1);

        const xml_domain = "[[&quot;foo&quot;,&quot;=&quot;,&quot;Gently Weeps&quot;]]";

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewArch: `
                    <search>
                        <filter string="Foo" name="gently_weeps" domain="${xml_domain}"/>
                    </search>
                `,
            context: { search_default_gently_weeps: 1 },
        });

        assert.deepEqual(
            getDomain(controlPanel),
            [["foo", "=", "Gently Weeps"]],
            "A JSON parsable xml domain should be handled just like any other"
        );
    });

    QUnit.test("filter with date attribute set as search_default", async function (assert) {
        assert.expect(1);

        patchDate(2019, 6, 31, 13, 43, 0);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewArch: `
                    <search>
                        <filter string="Date" name="date_field" date="date_field" default_period="last_month"/>
                    </search>
                `,
            context: { search_default_date_field: true },
        });

        assert.deepEqual(getFacetTexts(controlPanel), ["Date: June 2019"]);
    });

    QUnit.test("filter domains are correcly combined by OR and AND", async function (assert) {
        assert.expect(2);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewArch: `
                    <search>
                        <filter string="Filter Group 1" name="f_1_g1" domain="[['foo', '=', 'f1_g1']]"/>
                        <separator/>
                        <filter string="Filter 1 Group 2" name="f1_g2" domain="[['foo', '=', 'f1_g2']]"/>
                        <filter string="Filter 2 GROUP 2" name="f2_g2" domain="[['foo', '=', 'f2_g2']]"/>
                    </search>
                `,
            context: {
                search_default_f_1_g1: true,
                search_default_f1_g2: true,
                search_default_f2_g2: true,
            },
        });

        assert.deepEqual(getDomain(controlPanel), [
            "&",
            ["foo", "=", "f1_g1"],
            "|",
            ["foo", "=", "f1_g2"],
            ["foo", "=", "f2_g2"],
        ]);

        assert.deepEqual(getFacetTexts(controlPanel), [
            "Filter Group 1",
            "Filter 1 Group 2orFilter 2 GROUP 2",
        ]);
    });

    QUnit.test("arch order of groups of filters preserved", async function (assert) {
        assert.expect(12);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewArch: `
                    <search>
                        <filter string="1" name="coolName1" date="date_field"/>
                        <separator/>
                        <filter string="2" name="coolName2" date="date_field"/>
                        <separator/>
                        <filter string="3" name="coolName3" domain="[]"/>
                        <separator/>
                        <filter string="4" name="coolName4" domain="[]"/>
                        <separator/>
                        <filter string="5" name="coolName5" domain="[]"/>
                        <separator/>
                        <filter string="6" name="coolName6" domain="[]"/>
                        <separator/>
                        <filter string="7" name="coolName7" domain="[]"/>
                        <separator/>
                        <filter string="8" name="coolName8" domain="[]"/>
                        <separator/>
                        <filter string="9" name="coolName9" domain="[]"/>
                        <separator/>
                        <filter string="10" name="coolName10" domain="[]"/>
                        <separator/>
                        <filter string="11" name="coolName11" domain="[]"/>
                    </search>
                `,
        });

        await toggleFilterMenu(controlPanel);
        assert.containsN(controlPanel, ".o_filter_menu .o_menu_item", 11);

        const menuItemEls = controlPanel.el.querySelectorAll(".o_filter_menu .o_menu_item");
        [...menuItemEls].forEach((e, index) => {
            assert.strictEqual(e.innerText.trim(), String(index + 1));
        });
    });
});
