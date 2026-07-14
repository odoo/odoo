import { expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    getFacetTexts,
    mountWithSearch,
    removeFacet,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { defineSearchBarModels } from "./models";

import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { SearchBar } from "@web/search/search_bar/search_bar";

defineSearchBarModels();

test("simple rendering", async () => {
    mockDate("1997-01-09T12:00:00");

    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["filter", "comparison"],
        searchViewId: false,
    });
    expect(`.o_searchview_dropdown_toggler`).toHaveCount(1);
    expect(`.dropdown.o_comparison_menu`).toHaveCount(0);

    await toggleSearchBarMenu();
    await toggleMenuItem("Birthday");
    await toggleMenuItemOption("Birthday", "January");
    expect(`.o_comparison_menu .fa.fa-adjust`).toHaveCount(1);
    expect(`.o_comparison_menu .o_dropdown_title`).toHaveText(/^comparison$/i);
    expect(`.o_comparison_menu .dropdown-item`).toHaveCount(2);
    expect(`.o_comparison_menu .dropdown-item[role=menuitemcheckbox]`).toHaveCount(2);
    expect(queryAllTexts`.o_comparison_menu .dropdown-item`).toEqual([
        "Birthday: Previous Period",
        "Birthday: Previous Year",
    ]);
    expect(queryAll`.o_comparison_menu .dropdown-item`.map((e) => e.ariaChecked)).toEqual([
        "false",
        "false",
    ]);
});

test("activate a comparison works", async () => {
    mockDate("1997-01-09T12:00:00");

    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter", "comparison"],
        searchViewId: false,
    });
    await toggleSearchBarMenu();
    await toggleMenuItem("Birthday");
    await toggleMenuItemOption("Birthday", "January");
    await toggleMenuItem("Birthday: Previous Period");
    expect(getFacetTexts()).toEqual(["Birthday: January 1997", "Birthday: Previous Period"]);

    await toggleMenuItem("Date");
    await toggleMenuItemOption("Date", "December");
    await toggleMenuItem("Date: Previous Year");
    expect(getFacetTexts()).toEqual([
        ["Birthday: January 1997", "Date: December 1996"].join("\nor\n"),
        "Date: Previous Year",
    ]);

    await toggleMenuItemOption("Date", "1996");
    expect(getFacetTexts()).toEqual(["Birthday: January 1997"]);

    await toggleMenuItem("Birthday: Previous Year");
    expect(`.o_comparison_menu .dropdown-item`).toHaveCount(2);
    expect(`.o_comparison_menu .dropdown-item[role=menuitemcheckbox]`).toHaveCount(2);
    expect(queryAllTexts`.o_comparison_menu .dropdown-item`).toEqual([
        "Birthday: Previous Period",
        "Birthday: Previous Year",
    ]);
    expect(queryAll`.o_comparison_menu .dropdown-item`.map((e) => e.ariaChecked)).toEqual([
        "false",
        "true",
    ]);
    expect(getFacetTexts()).toEqual(["Birthday: January 1997", "Birthday: Previous Year"]);

    await removeFacet("Birthday: January 1997");
    expect(getFacetTexts()).toEqual([]);
});
