import { expect, test } from "@odoo/hoot";
import { queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import {
    contains,
    getFacetTexts,
    isItemSelected,
    isOptionSelected,
    mountWithSearch,
    removeFacet,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { defineSearchBarModels, Foo } from "./models";

import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { animationFrame } from "@odoo/hoot-mock";

defineSearchBarModels();

test("simple rendering with neither groupbys nor groupable fields", async () => {
    Foo._views[["search", false]] = `<search/>`;

    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewFields: {},
    });
    await toggleSearchBarMenu();
    expect(`.o_menu_item`).toHaveCount(0);
    expect(`.dropdown-divider`).toHaveCount(0);
    expect(`.o_add_custom_group_menu`).toHaveCount(0);
});

test("simple rendering with no groupby", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    await toggleSearchBarMenu();
    expect(`.o_menu_item`).toHaveCount(1);
    expect(`.dropdown-divider`).toHaveCount(0);
    expect(`.o_add_custom_group_menu`).toHaveCount(1);
});

test("simple rendering with a single groupby", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
            </search>
        `,
    });
    await toggleSearchBarMenu();

    expect(`.o_menu_item`).toHaveCount(2);
    const menuItem = queryFirst`.o_menu_item`;
    expect(menuItem).toHaveText("Foo");
    expect(menuItem).toHaveAttribute("role", "menuitemcheckbox");
    expect(menuItem).toHaveProperty("ariaChecked", "false");
    expect(".dropdown-divider").toHaveCount(1);
    expect(".o_add_custom_group_menu").toHaveCount(1);
});

test(`toggle a "simple" groupby in groupby menu works`, async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
            </search>
        `,
    });
    await toggleSearchBarMenu();

    expect(searchBar.env.searchModel.groupBy).toEqual([]);
    expect(getFacetTexts()).toEqual([]);
    expect(isItemSelected("Foo")).toBe(false);

    const menuItem = queryFirst`.o_menu_item`;
    expect(menuItem).toHaveText("Foo");
    expect(menuItem).toHaveAttribute("role", "menuitemcheckbox");
    expect(menuItem).toHaveProperty("ariaChecked", "false");

    await toggleMenuItem("Foo");
    expect(menuItem).toHaveProperty("ariaChecked", "true");
    expect(searchBar.env.searchModel.groupBy).toEqual(["foo"]);
    expect(getFacetTexts()).toEqual(["Foo"]);
    expect(`.o_searchview .o_searchview_facet .o_searchview_facet_label`).toHaveCount(1);
    expect(isItemSelected("Foo")).toBe(true);

    await toggleMenuItem("Foo");
    expect(searchBar.env.searchModel.groupBy).toEqual([]);
    expect(getFacetTexts()).toEqual([]);
    expect(isItemSelected("Foo")).toBe(false);
});

test(`toggle a "simple" groupby quickly does not crash`, async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
            </search>
        `,
    });
    await toggleSearchBarMenu();

    toggleMenuItem("Foo");
    toggleMenuItem("Foo");
    await animationFrame();

    expect(isItemSelected("Foo")).toBe(false);
});

test(`remove a "Group By" facet properly unchecks groupbys in groupby menu`, async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
            </search>
        `,
        context: { search_default_group_by_foo: 1 },
    });
    await toggleSearchBarMenu();
    expect(getFacetTexts()).toEqual(["Foo"]);
    expect(searchBar.env.searchModel.groupBy).toEqual(["foo"]);
    expect(isItemSelected("Foo")).toBe(true);

    await removeFacet("Foo");
    expect(getFacetTexts()).toEqual([]);
    expect(searchBar.env.searchModel.groupBy).toEqual([]);

    await toggleSearchBarMenu();
    expect(isItemSelected("Foo")).toBe(false);
});

test("group by a date field using interval works", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Date" name="date" context="{'group_by': 'date_field:week'}"/>
            </search>
        `,
        context: { search_default_date: 1 },
    });
    await toggleSearchBarMenu();
    expect(searchBar.env.searchModel.groupBy).toEqual(["date_field:week"]);

    await toggleMenuItem("Date");
    expect(isOptionSelected("Date", "Week")).toBe(true);
    expect(queryAllTexts`.o_item_option`).toEqual(["Year", "Quarter", "Month", "Week", "Day"]);

    await toggleMenuItemOption("Date", "Year");
    expect(searchBar.env.searchModel.groupBy).toEqual(["date_field:year", "date_field:week"]);
    expect(getFacetTexts()).toEqual(["Date: Year\n>\nDate: Week"]);
    expect(isOptionSelected("Date", "Year")).toBe(true);
    expect(isOptionSelected("Date", "Week")).toBe(true);

    await toggleMenuItemOption("Date", "Month");
    expect(searchBar.env.searchModel.groupBy).toEqual([
        "date_field:year",
        "date_field:month",
        "date_field:week",
    ]);
    expect(getFacetTexts()).toEqual(["Date: Year\n>\nDate: Month\n>\nDate: Week"]);
    expect(isOptionSelected("Date", "Year")).toBe(true);
    expect(isOptionSelected("Date", "Month")).toBe(true);
    expect(isOptionSelected("Date", "Week")).toBe(true);

    await toggleMenuItemOption("Date", "Week");
    expect(searchBar.env.searchModel.groupBy).toEqual(["date_field:year", "date_field:month"]);
    expect(getFacetTexts()).toEqual(["Date: Year\n>\nDate: Month"]);
    expect(isOptionSelected("Date", "Year")).toBe(true);
    expect(isOptionSelected("Date", "Month")).toBe(true);

    await toggleMenuItemOption("Date", "Month");
    expect(searchBar.env.searchModel.groupBy).toEqual(["date_field:year"]);
    expect(getFacetTexts()).toEqual(["Date: Year"]);
    expect(isOptionSelected("Date", "Year")).toBe(true);

    await toggleMenuItemOption("Date", "Year");
    expect(searchBar.env.searchModel.groupBy).toEqual([]);
    expect(getFacetTexts()).toEqual([]);
});

test("interval options are correctly grouped and ordered", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "foo",
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
    expect(getFacetTexts()).toEqual(["Bar"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    await toggleMenuItemOption("Date", "Week");
    expect(getFacetTexts()).toEqual(["Bar\n>\nDate: Week"]);

    await toggleMenuItemOption("Date", "Day");
    expect(getFacetTexts()).toEqual(["Bar\n>\nDate: Week\n>\nDate: Day"]);

    await toggleMenuItemOption("Date", "Year");
    expect(getFacetTexts()).toEqual(["Bar\n>\nDate: Year\n>\nDate: Week\n>\nDate: Day"]);

    await toggleMenuItem("Foo");
    expect(getFacetTexts()).toEqual(["Bar\n>\nDate: Year\n>\nDate: Week\n>\nDate: Day\n>\nFoo"]);

    await toggleMenuItemOption("Date", "Quarter");
    expect(getFacetTexts()).toEqual([
        "Bar\n>\nDate: Year\n>\nDate: Quarter\n>\nDate: Week\n>\nDate: Day\n>\nFoo",
    ]);

    await toggleMenuItem("Bar");
    expect(getFacetTexts()).toEqual([
        "Date: Year\n>\nDate: Quarter\n>\nDate: Week\n>\nDate: Day\n>\nFoo",
    ]);

    await toggleMenuItemOption("Date", "Week");
    expect(getFacetTexts()).toEqual(["Date: Year\n>\nDate: Quarter\n>\nDate: Day\n>\nFoo"]);
});

test("default groupbys can be ordered", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
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
    expect(searchBar.env.searchModel.groupBy).toEqual(["date_field:week", "birthday:month"]);
    expect(getFacetTexts()).toEqual(["Date: Week\n>\nBirthday: Month"]);
});

test("a separator in groupbys does not cause problems", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "foo",
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
    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    await toggleMenuItemOption("Date", "Day");
    expect(isItemSelected("Date")).toBe(true);
    expect(isItemSelected("Bar")).toBe(false);
    expect(isOptionSelected("Date", "Day")).toBe(true);
    expect(getFacetTexts()).toEqual(["Date: Day"]);

    await toggleMenuItem("Bar");
    expect(isItemSelected("Date")).toBe(true);
    expect(isItemSelected("Bar")).toBe(true);
    expect(isOptionSelected("Date", "Day")).toBe(true);
    expect(getFacetTexts()).toEqual(["Date: Day\n>\nBar"]);

    await toggleMenuItemOption("Date", "Quarter");
    expect(isItemSelected("Date")).toBe(true);
    expect(isItemSelected("Bar")).toBe(true);
    expect(isOptionSelected("Date", "Quarter")).toBe(true);
    expect(isOptionSelected("Date", "Day")).toBe(true);
    expect(getFacetTexts()).toEqual(["Date: Quarter\n>\nDate: Day\n>\nBar"]);

    await toggleMenuItem("Bar");
    expect(isItemSelected("Date")).toBe(true);
    expect(isItemSelected("Bar")).toBe(false);
    expect(isOptionSelected("Date", "Quarter")).toBe(true);
    expect(isOptionSelected("Date", "Day")).toBe(true);
    expect(getFacetTexts()).toEqual(["Date: Quarter\n>\nDate: Day"]);

    await contains(`.o_facet_remove`).click();
    expect(getFacetTexts()).toEqual([]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    expect(isItemSelected("Date")).toBe(false);
    expect(isItemSelected("Bar")).toBe(false);
    expect(isOptionSelected("Date", "Quarter")).toBe(false);
    expect(isOptionSelected("Date", "Day")).toBe(false);
});

test("falsy search default groupbys are not activated", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
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
    expect(searchBar.env.searchModel.groupBy).toEqual([]);
    expect(getFacetTexts()).toEqual([]);
});

test("Custom group by menu is displayed when hideCustomGroupBy is not set", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
            </search>
        `,
        searchMenuTypes: ["groupBy"],
    });
    await toggleSearchBarMenu();
    expect(`.o_add_custom_group_menu`).toHaveCount(1);
});

test("Custom group by menu is displayed when hideCustomGroupBy is false", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
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
    await toggleSearchBarMenu();
    expect(`.o_add_custom_group_menu`).toHaveCount(1);
});

test("Custom group by menu is displayed when hideCustomGroupBy is true", async () => {
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
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
    await toggleSearchBarMenu();
    expect(`.o_add_custom_group_menu`).toHaveCount(0);
});
