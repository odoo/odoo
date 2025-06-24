import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import {
    clickOnButtonAddBranch,
    clickOnButtonAddNewRule,
    getCurrentPath,
    openModelFieldSelectorPopover,
    selectOperator,
    selectValue,
} from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineModels,
    fields,
    getFacetTexts,
    isItemSelected,
    isOptionSelected,
    mockService,
    models,
    mountWithSearch,
    onRpc,
    openAddCustomFilterDialog,
    serverState,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { Foo, Partner, defineSearchBarModels } from "./models";

import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";

defineSearchBarModels();

test("simple rendering with no filter", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
    });
    await toggleSearchBarMenu();
    expect(".o_menu_item").toHaveCount(1);
    expect(".dropdown-divider").toHaveCount(0);
    expect(".dropdown-item").toHaveCount(1);
    expect(`.dropdown-item`).toHaveText("Add Custom Filter");
});

test("simple rendering with a single filter", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Foo" name="foo" domain="[]"/>
            </search>
        `,
    });
    await toggleSearchBarMenu();
    expect(`.o_menu_item`).toHaveCount(2);
    expect(`.o_menu_item[role=menuitemcheckbox]`).toHaveCount(1);
    expect(queryFirst`.o_menu_item`).toHaveProperty("ariaChecked", "false");
    expect(`.dropdown-divider`).toHaveCount(1);
    expect(`.o_menu_item:nth-of-type(2)`).toHaveText("Add Custom Filter");
});

test(`toggle a "simple" filter in filter menu works`, async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Foo" name="foo" domain="[('foo', '=', 'qsdf')]"/>
            </search>
        `,
    });
    await toggleSearchBarMenu();
    expect(getFacetTexts()).toEqual([]);
    expect(isItemSelected("Foo")).toBe(false);
    expect(searchBar.env.searchModel.domain).toEqual([]);
    expect(".o_menu_item[role=menuitemcheckbox]").toHaveCount(1);
    expect(queryFirst`.o_menu_item`).toHaveProperty("ariaChecked", "false");

    await toggleMenuItem("Foo");
    expect(queryFirst`.o_menu_item`).toHaveProperty("ariaChecked", "true");
    expect(getFacetTexts()).toEqual(["Foo"]);
    expect(`.o_searchview .o_searchview_facet .o_searchview_facet_label`).toHaveCount(1);
    expect(isItemSelected("Foo")).toBe(true);
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "=", "qsdf"]]);

    await toggleMenuItem("Foo");
    expect(getFacetTexts()).toEqual([]);
    expect(isItemSelected("Foo")).toBe(false);
    expect(searchBar.env.searchModel.domain).toEqual([]);
});

test("filter by a date field using period works", async () => {
    mockDate("2017-03-22T01:00:00");

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="date_field" date="date_field"/>
            </search>
        `,
        context: { search_default_date_field: 1 },
    });
    await toggleSearchBarMenu();
    await toggleMenuItem("Date");

    // default filter should be activated with the global default period 'this_month'
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-03-01"],
        ["date_field", "<=", "2017-03-31"],
    ]);
    expect(isItemSelected("Date")).toBe(true);
    expect(isOptionSelected("Date", "March")).toBe(true);
    expect(queryAllTexts`.o-dropdown--menu .o_item_option`).toEqual([
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
    ]);

    await toggleMenuItemOption("Date", "March");
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-01-01"],
        ["date_field", "<=", "2017-12-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: 2017"]);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "February");
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-02-01"],
        ["date_field", "<=", "2017-02-28"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: February 2017"]);
    expect(isOptionSelected("Date", "February")).toBe(true);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "February");
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-01-01"],
        ["date_field", "<=", "2017-12-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: 2017"]);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "January");
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-01-01"],
        ["date_field", "<=", "2017-01-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: January 2017"]);
    expect(isOptionSelected("Date", "January")).toBe(true);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "Q4");
    expect(searchBar.env.searchModel.domain).toEqual([
        "|",
        "&",
        ["date_field", ">=", "2017-01-01"],
        ["date_field", "<=", "2017-01-31"],
        "&",
        ["date_field", ">=", "2017-10-01"],
        ["date_field", "<=", "2017-12-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: January 2017/Q4 2017"]);
    expect(isOptionSelected("Date", "January")).toBe(true);
    expect(isOptionSelected("Date", "Q4")).toBe(true);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "January");
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-10-01"],
        ["date_field", "<=", "2017-12-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: Q4 2017"]);
    expect(isOptionSelected("Date", "Q4")).toBe(true);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "Q4");
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-01-01"],
        ["date_field", "<=", "2017-12-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: 2017"]);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "Q1");
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-01-01"],
        ["date_field", "<=", "2017-03-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: Q1 2017"]);
    expect(isOptionSelected("Date", "Q1")).toBe(true);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "Q1");
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-01-01"],
        ["date_field", "<=", "2017-12-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: 2017"]);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "2017");
    expect(searchBar.env.searchModel.domain).toEqual([]);
    expect(getFacetTexts()).toEqual([]);

    await toggleMenuItemOption("Date", "2017");
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2017-01-01"],
        ["date_field", "<=", "2017-12-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: 2017"]);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "2016");
    expect(searchBar.env.searchModel.domain).toEqual([
        "|",
        "&",
        ["date_field", ">=", "2016-01-01"],
        ["date_field", "<=", "2016-12-31"],
        "&",
        ["date_field", ">=", "2017-01-01"],
        ["date_field", "<=", "2017-12-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: 2016/2017"]);
    expect(isOptionSelected("Date", "2016")).toBe(true);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "2015");
    expect(searchBar.env.searchModel.domain).toEqual([
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
    ]);
    expect(getFacetTexts()).toEqual(["Date: 2015/2016/2017"]);
    expect(isOptionSelected("Date", "2015")).toBe(true);
    expect(isOptionSelected("Date", "2016")).toBe(true);
    expect(isOptionSelected("Date", "2017")).toBe(true);

    await toggleMenuItemOption("Date", "March");
    expect(searchBar.env.searchModel.domain).toEqual([
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
    ]);
    expect(getFacetTexts()).toEqual(["Date: March 2015/March 2016/March 2017"]);
    expect(isOptionSelected("Date", "March")).toBe(true);
    expect(isOptionSelected("Date", "2015")).toBe(true);
    expect(isOptionSelected("Date", "2016")).toBe(true);
    expect(isOptionSelected("Date", "2017")).toBe(true);
});

test("filter by a date field using period works even in January", async () => {
    mockDate("2017-01-07T03:00:00");

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="some_filter" date="date_field" default_period="month-1"/>
            </search>
        `,
        context: { search_default_some_filter: 1 },
    });
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2016-12-01"],
        ["date_field", "<=", "2016-12-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: December 2016"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    expect(isItemSelected("Date")).toBe(true);
    expect(isOptionSelected("Date", "December")).toBe(true);
    expect(isOptionSelected("Date", "2016")).toBe(true);
});

test("filter by a date field using period works even with an endYear in the past", async () => {
    mockDate("2017-01-07T03:00:00");

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="some_filter" date="date_field" start_year="-4" end_year="-2"/>
            </search>
        `,
        context: { search_default_some_filter: 1 },
    });
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2015-01-01"],
        ["date_field", "<=", "2015-01-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: January 2015"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    expect(isItemSelected("Date")).toBe(true);
    expect(isOptionSelected("Date", "January")).toBe(true);
    expect(isOptionSelected("Date", "2015")).toBe(true);

    await toggleMenuItemOption("Date", "2015");
    expect(isOptionSelected("Date", "January")).toBe(false);

    await toggleMenuItemOption("Date", "December");
    expect(isItemSelected("Date")).toBe(true);
    expect(isOptionSelected("Date", "December")).toBe(true);
    expect(isOptionSelected("Date", "2014")).toBe(true);
});

test("filter by a date field using period works even with a startYear in the future", async () => {
    mockDate("2017-01-07T03:00:00");

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="some_filter" date="date_field" start_year="2" end_year="4"/>
            </search>
        `,
        context: { search_default_some_filter: 1 },
    });
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["date_field", ">=", "2019-01-01"],
        ["date_field", "<=", "2019-01-31"],
    ]);
    expect(getFacetTexts()).toEqual(["Date: January 2019"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    expect(isItemSelected("Date")).toBe(true);
    expect(isOptionSelected("Date", "January")).toBe(true);
    expect(isOptionSelected("Date", "2019")).toBe(true);

    await toggleMenuItemOption("Date", "2019");
    expect(isOptionSelected("Date", "January")).toBe(false);

    await toggleMenuItemOption("Date", "December");
    expect(isItemSelected("Date")).toBe(true);
    expect(isOptionSelected("Date", "December")).toBe(true);
    expect(isOptionSelected("Date", "2019")).toBe(true);
});

test("`context` key in <filter> is used", async () => {
    const searchBarMenu = await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Filter" name="some_filter" domain="[]" context="{'coucou_1': 1}"/>
            </search>
        `,
        context: { search_default_some_filter: 1 },
    });
    expect(searchBarMenu.env.searchModel.context).toEqual({
        coucou_1: 1,
        lang: "en",
        tz: "taht",
        uid: 7,
        allowed_company_ids: [1],
    });
});

test("Filter with JSON-parsable domain works", async () => {
    const searchBarMenu = await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Foo" name="gently_weeps" domain="[[&quot;foo&quot;,&quot;=&quot;,&quot;Gently Weeps&quot;]]"/>
            </search>
        `,
        context: { search_default_gently_weeps: 1 },
    });
    expect(searchBarMenu.env.searchModel.domain).toEqual([["foo", "=", "Gently Weeps"]]);
});

test("filter with date attribute set as search_default", async () => {
    mockDate("2019-07-31T13:43:00");

    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="date_field" date="date_field" default_period="month-1"/>
            </search>
        `,
        context: { search_default_date_field: true },
    });
    expect(getFacetTexts()).toEqual(["Date: June 2019"]);
});

test("filter with multiple values in default_period date attribute set as search_default", async () => {
    mockDate("2019-07-31T13:43:00");

    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="date_field" date="date_field" default_period="year,year-1"/>
            </search>
        `,
        context: { search_default_date_field: true },
    });
    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    expect(isItemSelected("Date")).toBe(true);
    expect(isOptionSelected("Date", "2019")).toBe(true);
    expect(isOptionSelected("Date", "2018")).toBe(true);
});

test("date filter with custom option set as default_period", async () => {
    mockDate("2019-07-31T13:43:00");

    const searchBarMenu = await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="date_field" date="date_field" default_period="custom_date_field_today">
                    <filter name="date_field_today" string="Today" domain="[('date_field', '=', context_today().strftime('%Y-%m-%d'))]"/>
                </filter>
            </search>
        `,
        context: { search_default_date_field: true },
    });
    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    expect(isItemSelected("Date")).toBe(true);
    expect(isOptionSelected("Date", "Today")).toBe(true);
    expect(searchBarMenu.env.searchModel.domain).toEqual([["date_field", "=", "2019-07-31"]]);
});

test("date filter with default_period in the context", async () => {
    mockDate("2019-07-31T13:43:00");

    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="date_field" date="date_field" default_period="custom_date_field_today">
                    <filter name="date_field_today" string="Today" domain="[('date_field', '=', context_today().strftime('%Y-%m-%d'))]"/>
                </filter>
            </search>
        `,
        context: { search_default_date_field: "year-1,month-1" },
    });
    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    expect(isItemSelected("Date")).toBe(true);
    expect(isOptionSelected("Date", "June")).toBe(true);
    expect(isOptionSelected("Date", "2018")).toBe(true);
});

for (const contextValue of ["True", "1"]) {
    test(`date filter with search_default with a value of "${contextValue}" in the context`, async () => {
        mockDate("2019-07-31T13:43:00");
        const searchBarMenu = await mountWithSearch(SearchBarMenu, {
            resModel: "foo",
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewArch: `
                <search>
                    <filter string="Date" name="date_field" date="date_field" default_period="custom_date_field_today">
                        <filter name="date_field_today" string="Today" domain="[('date_field', '=', context_today().strftime('%Y-%m-%d'))]"/>
                    </filter>
                </search>
            `,
            context: { search_default_date_field: contextValue },
        });
        await toggleSearchBarMenu();
        await toggleMenuItem("Date");
        expect(isItemSelected("Date")).toBe(true);
        expect(isOptionSelected("Date", "Today")).toBe(true);
        expect(searchBarMenu.env.searchModel.domain).toEqual([["date_field", "=", "2019-07-31"]]);
    });
}

test("filter domains are correcly combined by OR and AND", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
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
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["foo", "=", "f1_g1"],
        "|",
        ["foo", "=", "f1_g2"],
        ["foo", "=", "f2_g2"],
    ]);
    expect(getFacetTexts()).toEqual(["Filter Group 1", "Filter 1 Group 2\nor\nFilter 2 GROUP 2"]);
});

test("arch order of groups of filters preserved", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
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
    await toggleSearchBarMenu();
    expect(`.o_filter_menu .o_menu_item`).toHaveCount(12);
    expect(queryAllTexts`.o_filter_menu .o_menu_item:not(.o_add_custom_filter)`).toEqual(
        "1,2,3,4,5,6,7,8,9,10,11".split(",")
    );
});

test("Open 'Add Custom Filter' dialog", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search></search>`,
    });
    await toggleSearchBarMenu();
    expect(queryAllTexts`.o_filter_menu .dropdown-item`).toEqual(["Add Custom Filter"]);
    expect(".modal").toHaveCount(0);

    await openAddCustomFilterDialog();
    expect(".modal").toHaveCount(1);
    expect(".modal header").toHaveText("Add Custom Filter");
    expect(".modal .o_domain_selector").toHaveCount(1);
    expect(".modal .o_domain_selector .o_tree_editor_condition").toHaveCount(1);
    expect(queryAllTexts`.modal footer button`).toEqual(["Add", "Cancel"]);
});

test("Default leaf in 'Add Custom Filter' dialog is based on ID (if no special fields on model)", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search/>`,
    });
    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    expect(".modal .o_domain_selector .o_tree_editor_condition").toHaveCount(1);
    expect(".o_tree_editor_condition .o_model_field_selector_chain_part").toHaveCount(1);
    expect(getCurrentPath()).toBe("Id");
});

test("Default leaf in 'Add Custom Filter' dialog is based on first special field (if any special fields on model)", async () => {
    defineModels([class Country extends models.Model {}]);
    Foo._fields.country_id = fields.Many2one({ string: "Country", relation: "country" });
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search/>`,
    });
    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    expect(".modal .o_domain_selector .o_tree_editor_condition").toHaveCount(1);
    expect(".o_tree_editor_condition .o_model_field_selector_chain_part").toHaveCount(1);
    expect(getCurrentPath()).toBe("Country");
});

test("Default connector is '|' (any)", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search/>`,
    });
    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    expect(".modal .o_domain_selector .o_tree_editor_condition").toHaveCount(1);
    expect(".o_tree_editor_condition .o_model_field_selector_chain_part").toHaveCount(1);
    expect(getCurrentPath()).toBe("Id");
    expect(".o_domain_selector .o_tree_editor_connector").toHaveCount(1);

    await clickOnButtonAddNewRule();
    expect(".o_domain_selector .dropdown-toggle").toHaveCount(1);
    expect(".o_domain_selector .dropdown-toggle").toHaveText("any");
    expect(".modal .o_domain_selector .o_tree_editor_condition").toHaveCount(2);
});

test("Add a custom filter", async () => {
    onRpc("/web/domain/validate", () => true);
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Filter" name="filter" domain="[('foo', '=', 'abc')]"/>
            </search>
        `,
        context: {
            search_default_filter: true,
        },
    });
    expect(getFacetTexts()).toEqual(["Filter"]);
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "=", "abc"]]);

    await toggleSearchBarMenu();
    expect(".o_filter_menu .o_menu_item:not(.o_add_custom_filter)").toHaveCount(1);

    await openAddCustomFilterDialog();
    await clickOnButtonAddNewRule();
    await contains(".o_domain_selector .dropdown-toggle").click();
    await contains(queryFirst(".dropdown-menu .dropdown-item")).click();

    await clickOnButtonAddBranch(-1);
    await clickOnButtonAddBranch(-1);
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([
        "Filter",
        "Id = 1",
        "Id = 1",
        "( Id = 1 and Id = 1 ) or Id is in ( 1 , 1 )",
    ]);
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["foo", "=", "abc"],
        "&",
        ["id", "=", 1],
        "&",
        ["id", "=", 1],
        "|",
        "|",
        ["id", "=", 1],
        ["id", "=", 1],
        "&",
        ["id", "=", 1],
        ["id", "=", 1],
    ]);

    // open again the search menu -> the custom filter should not be displayed
    await toggleSearchBarMenu();
    expect(".o_filter_menu .o_menu_item:not(.o_add_custom_filter)").toHaveCount(1);
});

test("Add a custom filter containing an expression", async () => {
    serverState.debug = "1";

    onRpc("/web/domain/validate", () => true);
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search />`,
    });
    expect(getFacetTexts()).toEqual([]);
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    await contains(`.o_domain_selector_debug_container textarea`).edit(
        `[("foo", "in", [uid, 1, "a"])]`
    );
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([`Foo is in ( uid , 1 , "a" )`]);
    expect(searchBar.env.searchModel.domain).toEqual([
        ["foo", "in", [7, 1, "a"]], // uid = 7
    ]);
});

test("Add a custom filter containing a between operator", async () => {
    serverState.debug = "1";

    onRpc("/web/domain/validate", () => true);
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search />`,
    });
    expect(getFacetTexts()).toEqual([]);
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    await contains(`.o_domain_selector_debug_container textarea`).edit(
        `[("id", "between", [0, 10])]`
    );
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([`Id is between 0 and 10`]);
    expect(searchBar.env.searchModel.domain).toEqual(["&", ["id", ">=", 0], ["id", "<=", 10]]);
});

test("consistent display of ! in debug mode", async () => {
    serverState.debug = "1";

    onRpc("/web/domain/validate", () => true);
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search />`,
    });
    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    await contains(`.o_domain_selector_debug_container textarea`).edit(
        `["!", "|", ("foo", "=", 1 ), ("id", "=", 2)]`
    );
    expect(".o_tree_editor_row .dropdown-toggle").toHaveText("none");

    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([`! ( Foo = 1 or Id = 2 )`]);
    expect(searchBar.env.searchModel.domain).toEqual(["!", "|", ["foo", "=", 1], ["id", "=", 2]]);
});

test("display of is (not) (not) set in facets", async () => {
    Foo._fields.boolean = fields.Boolean();
    onRpc("/web/domain/validate", () => true);
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search/>`,
    });
    expect(getFacetTexts()).toEqual([]);
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    await selectOperator("not_set");
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual(["Id is not set"]);
    expect(searchBar.env.searchModel.domain).toEqual([["id", "=", false]]);

    await contains(".o_searchview_facet_label").click();
    await selectOperator("set");
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual(["Id is set"]);
    expect(searchBar.env.searchModel.domain).toEqual([["id", "!=", false]]);

    await contains(".o_searchview_facet_label").click();
    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item_name:contains(Boolean)").click();
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual(["Boolean is set"]);
    expect(searchBar.env.searchModel.domain).toEqual([["boolean", "=", true]]);

    await contains(".o_searchview_facet_label").click();
    await selectValue(false);
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual(["Boolean is not set"]);
    expect(searchBar.env.searchModel.domain).toEqual([["boolean", "=", false]]);

    await contains(".o_searchview_facet_label").click();
    await selectOperator("is_not");
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual(["Boolean is not not set"]);
    expect(searchBar.env.searchModel.domain).toEqual([["boolean", "!=", false]]);

    await contains(".o_searchview_facet_label").click();
    await selectValue(true);
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual(["Boolean is not set"]);
    expect(searchBar.env.searchModel.domain).toEqual([["boolean", "!=", true]]);
});

test("Add a custom filter: notification on invalid domain", async () => {
    serverState.debug = "1";
    mockService("notification", {
        add(message, options) {
            expect.step("notification");
            expect(message).toBe("Domain is invalid. Please correct it");
            expect(options).toEqual({ type: "danger" });
        },
    });

    onRpc("/web/domain/validate", () => false);
    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search/>`,
    });

    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    await contains(`.o_domain_selector_debug_container textarea`).edit(`[(uid, uid, uid)]`);
    await contains(".modal footer button").click();
    expect(".modal .o_domain_selector").toHaveCount(1);
    expect.verifySteps(["notification"]);
});

test("display names in facets", async () => {
    serverState.debug = "1";
    Partner._records = [
        { id: 1, name: "John" },
        { id: 2, name: "David" },
    ];

    onRpc("/web/domain/validate", () => true);
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search />`,
    });
    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    await contains(`.o_domain_selector_debug_container textarea`).edit(
        `[("bar", "=", 1 ), ("bar", "in", [2, 5555]), ("bar", "!=", false), ("id", "=", 2)]`
    );
    await contains(".modal footer button").click();

    expect(getFacetTexts()).toEqual([
        "Bar = John",
        "Bar is in ( David , Inaccessible/missing record ID: 5555 )",
        "Bar != false",
        "Id = 2",
    ]);
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["bar", "=", 1],
        "&",
        ["bar", "in", [2, 5555]],
        "&",
        ["bar", "!=", false],
        ["id", "=", 2],
    ]);
});

test("display names in facets (with a property)", async () => {
    serverState.debug = "1";
    Partner._records = [{ id: 1, name: "John" }];

    onRpc("/web/domain/validate", () => true);
    onRpc("parent.model", "web_search_read", () => ({
        records: [
            {
                id: 1337,
                display_name: "First Parent",
                properties_definition: [
                    {
                        name: "m2o",
                        type: "many2one",
                        string: "M2O",
                        comodel: "partner",
                    },
                ],
            },
        ],
    }));

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search />`,
    });
    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    await contains(`.o_domain_selector_debug_container textarea`).edit(
        `[("properties.m2o", "=", 1)]`
    );
    await contains(".modal footer button").click();

    expect(getFacetTexts()).toEqual(["Properties \u2794 M2O = John"]);
    expect(searchBar.env.searchModel.domain).toEqual([["properties.m2o", "=", 1]]);
});

test("group by properties", async () => {
    onRpc("web_search_read", () => {
        expect.step("definitionFetched");
        return {
            records: [
                {
                    id: 1337,
                    display_name: "First Parent",
                    properties_definition: [
                        {
                            name: "my_text",
                            type: "text",
                            string: "My Text",
                        },
                        {
                            name: "my_partner",
                            type: "many2one",
                            string: "My Partner",
                            comodel: "partner",
                        },
                        {
                            name: "my_datetime",
                            type: "datetime",
                            string: "My Datetime",
                        },
                    ],
                },
                {
                    id: 1338,
                    display_name: "Second Parent",
                    properties_definition: [
                        {
                            name: "my_integer",
                            type: "integer",
                            string: "My Integer",
                        },
                    ],
                },
            ],
        };
    });

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Properties" name="properties" context="{'group_by': 'properties'}"/>
            </search>
        `,
        hideCustomGroupBy: true,
        searchMenuTypes: ["groupBy"],
    });
    // definition is fetched only when we open the properties menu
    expect.verifySteps([]);

    await contains(".o_searchview_dropdown_toggler").click();
    // definition is fetched only when we open the properties menu
    expect.verifySteps([]);
    expect(queryAllTexts`.o_menu_item`).toEqual(["Properties"]);

    await contains(".o_accordion_toggle").click();
    await animationFrame();
    // now that we open the properties we fetch the definition
    expect.verifySteps(["definitionFetched"]);
    expect(queryAllTexts`.o_accordion_values .dropdown-item`).toEqual([
        "My Text (First Parent)",
        "My Partner (First Parent)",
        "My Datetime (First Parent)",
        "My Integer (Second Parent)",
    ]);

    // open the datetime item
    await contains(queryAll`.o_accordion_values .dropdown-item`[2]).click();
    expect(queryAllTexts`.o_accordion_values .o_accordion_values .dropdown-item`).toEqual([
        "Year",
        "Quarter",
        "Month",
        "Week",
        "Day",
    ]);
    expect(searchBar.env.searchModel.groupBy).toEqual([]);
    expect(getFacetTexts()).toEqual([]);

    await contains(queryAll`.o_accordion_values .o_accordion_values .dropdown-item`[1]).click();
    await animationFrame();
    expect(searchBar.env.searchModel.groupBy).toEqual(["properties.my_datetime:quarter"]);
    expect(getFacetTexts()).toEqual(["My Datetime: Quarter"]);
});

test("shorten descriptions of long lists", async function () {
    serverState.debug = "1";
    onRpc("/web/domain/validate", () => true);
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `<search />`,
    });
    expect(getFacetTexts()).toEqual([]);
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    const values = new Array(500).fill(42525245);
    await contains(`.o_domain_selector_debug_container textarea`).edit(
        `[("id", "in", [${values}])]`
    );
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([`Id is in ( ${values.slice(0, 20).join(" , ")} , ... )`]);
    expect(searchBar.env.searchModel.domain).toEqual([["id", "in", values]]);
});
