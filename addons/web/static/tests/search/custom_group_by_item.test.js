import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    defineModels,
    fields,
    getFacetTexts,
    isItemSelected,
    isOptionSelected,
    models,
    mountWithSearch,
    selectGroup,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

import { SearchBar } from "@web/search/search_bar/search_bar";

class Foo extends models.Model {
    bar = fields.Many2one({ relation: "partner", groupable: false });
    birthday = fields.Date({ groupable: true });
    date_field = fields.Date({ string: "Date", groupable: true });
    float_field = fields.Float({ string: "Float", groupable: false });
    foo = fields.Char({ groupable: true });

    _views = {
        search: `<search/>`,
    };
}

class Partner extends models.Model {}

defineModels([Foo, Partner]);

test(`simple rendering`, async () => {
    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });

    await toggleSearchBarMenu();
    expect(`.o_group_by_menu option[disabled]`).toHaveText(`Add Custom Group`);
    expect(queryAllTexts`.o_add_custom_group_menu option:not([disabled])`).toEqual([
        "Birthday",
        "Created on",
        "Date",
        "Display name",
        "Foo",
        "Last Modified on",
    ]);
});

test(`the ID field should not be proposed in "Add Custom Group" menu`, async () => {
    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewFields: {
            foo: { string: "Foo", type: "char", store: true, sortable: true, groupable: true },
            id: { string: "ID", type: "integer", sortable: true, groupable: true },
        },
    });

    await toggleSearchBarMenu();
    expect(queryAllTexts`.o_add_custom_group_menu option:not([disabled])`).toEqual(["Foo"]);
});

test(`stored many2many should be proposed in "Add Custom Group" menu`, async () => {
    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewFields: {
            char_a: {
                string: "Char A",
                type: "char",
                store: true,
                sortable: true,
                groupable: true,
            },
            m2m_no_stored: { string: "M2M Not Stored", type: "many2many" },
            m2m_stored: {
                string: "M2M Stored",
                type: "many2many",
                store: true,
                groupable: true,
            },
        },
    });

    await toggleSearchBarMenu();
    expect(queryAllTexts`.o_add_custom_group_menu option:not([disabled])`).toEqual([
        "Char A",
        "M2M Stored",
    ]);
});

test(`add a date field in "Add Custom Group" activate a groupby with global default option "month"`, async () => {
    const component = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewFields: {
            date_field: {
                string: "Date",
                type: "date",
                store: true,
                sortable: true,
                groupable: true,
            },
            id: { sortable: true, string: "ID", type: "integer", groupable: true },
        },
    });

    await toggleSearchBarMenu();
    expect(component.env.searchModel.groupBy).toEqual([]);
    expect(`.o_add_custom_group_menu`).toHaveCount(1); // Add Custom Group

    await selectGroup("date_field");
    expect(component.env.searchModel.groupBy).toEqual(["date_field:month"]);
    expect(getFacetTexts()).toEqual(["Date: Month"]);
    expect(isItemSelected("Date")).toBe(true);

    await toggleMenuItem("Date");
    expect(isOptionSelected("Date", "Month")).toBe(true);
});

test(`click on add custom group toggle group selector`, async () => {
    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewFields: {
            date: {
                sortable: true,
                name: "date",
                string: "Super Date",
                type: "date",
                groupable: true,
            },
        },
    });

    await toggleSearchBarMenu();
    expect(`.o_add_custom_group_menu option[disabled]`).toHaveText("Add Custom Group");

    // Single select node with a single option
    expect(`.o_add_custom_group_menu option:not([disabled])`).toHaveCount(1);
    expect(`.o_add_custom_group_menu option:not([disabled])`).toHaveText("Super Date");
});

test(`select a field name in Add Custom Group menu properly trigger the corresponding field`, async () => {
    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewFields: {
            candle_light: {
                sortable: true,
                groupable: true,
                string: "Candlelight",
                type: "boolean",
            },
        },
    });

    await toggleSearchBarMenu();
    await selectGroup("candle_light");
    expect(`.o_group_by_menu .o_menu_item`).toHaveCount(2);
    expect(`.o_add_custom_group_menu`).toHaveCount(1);
    expect(getFacetTexts()).toEqual(["Candlelight"]);
});
