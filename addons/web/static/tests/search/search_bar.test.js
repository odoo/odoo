import { expect, test } from "@odoo/hoot";
import {
    clear,
    click,
    hover,
    keyDown,
    pointerDown,
    press,
    queryAll,
    queryAllTexts,
    queryAllValues,
    queryFirst,
    queryOne,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame, mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { Component, onWillUpdateProps, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineModels,
    editSearch,
    fields,
    getFacetTexts,
    models,
    onRpc,
    removeFacet,
    serverState,
    toggleMenuItem,
    toggleSearchBarMenu,
    validateSearch,
} from "@web/../tests/web_test_helpers";
import {
    SELECTORS,
    clickOnButtonDeleteNode,
    getCurrentOperator,
    getCurrentPath,
    getCurrentValue,
} from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import { mountWithSearch } from "./helpers";

import { SearchBar } from "@web/search/search_bar/search_bar";
import { browser } from "@web/core/browser/browser";

class Partner extends models.Model {
    name = fields.Char();
    bar = fields.Many2one({ relation: "partner" });
    birthday = fields.Date();
    birth_datetime = fields.Datetime({ string: "Birth DateTime" });
    foo = fields.Char();
    bool = fields.Boolean();
    company = fields.Many2one({ relation: "partner" });
    properties = fields.Properties({
        definition_record: "bar",
        definition_record_field: "child_properties",
    });
    child_properties = fields.PropertiesDefinition();

    _records = [
        {
            id: 1,
            name: "First record",
            foo: "yop",
            bar: 2,
            bool: true,
            birthday: "1983-07-15",
            birth_datetime: "1983-07-15 01:00:00",
        },
        {
            id: 2,
            name: "Second record",
            foo: "blip",
            bar: 1,
            bool: false,
            birthday: "1982-06-04",
            birth_datetime: "1982-06-04 02:00:00",
            company: 1,
        },
        {
            id: 3,
            name: "Third record",
            foo: "gnap",
            bar: 1,
            bool: false,
            birthday: "1985-09-13",
            birth_datetime: "1985-09-13 03:00:00",
            company: 5,
        },
        {
            id: 4,
            name: "Fourth record",
            foo: "plop",
            bar: 2,
            bool: true,
            birthday: "1983-05-05",
            birth_datetime: "1983-05-05 04:00:00",
        },
        {
            id: 5,
            name: "Fifth record",
            foo: "zoup",
            bar: 2,
            bool: true,
            birthday: "1800-01-01",
            birth_datetime: "1800-01-01 05:00:00",
        },
    ];
    _views = {
        list: `<tree><field name="foo"/></tree>`,
        search: `
            <search>
                <field name="foo"/>
                <field name="birthday"/>
                <field name="birth_datetime"/>
                <field name="bar" context="{'bar': self}"/>
                <field name="company" domain="[('bool', '=', True)]"/>
                <filter string="Birthday" name="date_filter" date="birthday"/>
                <filter string="Birthday" name="date_group_by" context="{'group_by': 'birthday:day'}"/>
            </search>
        `,
    };
}

defineModels([Partner]);

defineActions([
    {
        id: 1,
        name: "Partners Action",
        res_model: "partner",
        search_view_id: [false, "search"],
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    },
]);

test.tags`desktop`("basic rendering", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });
    expect(queryFirst`.o_searchview input`).toBeFocused();
});

test.tags`desktop`("navigation with facets", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        context: { search_default_date_group_by: 1 },
    });

    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(queryFirst`.o_searchview input`).toBeFocused();

    keyDown("ArrowLeft"); // press left to focus the facet
    expect(queryFirst`.o_searchview .o_searchview_facet`).toBeFocused();

    keyDown("ArrowRight"); // press right to focus the input
    expect(queryFirst`.o_searchview input`).toBeFocused();
});

test.tags`desktop`("navigation with facets (2)", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        context: {
            search_default_date_group_by: 1,
            search_default_foo: 1,
        },
    });

    expect(`.o_searchview .o_searchview_facet`).toHaveCount(2);
    expect(queryFirst`.o_searchview input`).toBeFocused();

    // press left to focus the rightmost facet
    keyDown("ArrowLeft");
    expect(queryFirst`.o_searchview .o_searchview_facet:nth-child(2)`).toBeFocused();

    // press left to focus the leftmost facet
    keyDown("ArrowLeft");
    expect(queryFirst`.o_searchview .o_searchview_facet:nth-child(1)`).toBeFocused();

    // press left to focus the input
    keyDown("ArrowLeft");
    expect(queryFirst`.o_searchview input`).toBeFocused();

    // press left to focus the leftmost facet
    keyDown("ArrowRight");
    expect(queryFirst`.o_searchview .o_searchview_facet:nth-child(1)`).toBeFocused();
});

test("search date and datetime fields. Support of timezones", async () => {
    mockTimeZone(6);

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    // Date case
    await editSearch("07/15/1983");
    keyDown("ArrowDown");
    keyDown("Enter");
    await animationFrame();
    expect(getFacetTexts().map((str) => str.replace(/\s+/g, " "))).toEqual(["Birthday 07/15/1983"]);
    expect(searchBar.env.searchModel.domain).toEqual([["birthday", "=", "1983-07-15"]]);

    // Close Facet
    click(`.o_searchview_facet .o_facet_remove`);

    // DateTime case
    await editSearch("07/15/1983 00:00:00");
    keyDown("ArrowDown");
    keyDown("Enter");
    await animationFrame();
    expect(getFacetTexts().map((str) => str.replace(/\s+/g, " "))).toEqual([
        "Birth DateTime 07/15/1983 00:00:00",
    ]);
    expect(searchBar.env.searchModel.domain).toEqual([
        ["birth_datetime", "=", "1983-07-14 18:00:00"],
    ]);
});

test("autocomplete menu clickout interactions", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
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
    expect(`.o_searchview_autocomplete`).toHaveCount(0);

    await editSearch("Hello there");
    expect(`.o_searchview input`).toHaveValue("Hello there");
    expect(`.o_searchview_autocomplete`).toHaveCount(1);

    keyDown("Escape");
    await animationFrame();
    expect(`.o_searchview input`).toHaveValue("");
    expect(`.o_searchview_autocomplete`).toHaveCount(0);

    await editSearch("General Kenobi");
    expect(`.o_searchview input`).toHaveValue("General Kenobi");
    expect(`.o_searchview_autocomplete`).toHaveCount(1);

    await contains(document.body).click();
    expect(`.o_searchview input`).toHaveValue("");
    expect(`.o_searchview_autocomplete`).toHaveCount(0);
});

test("select an autocomplete field", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    await editSearch("a");
    expect(`.o_searchview_autocomplete li`).toHaveCount(3);

    keyDown("Enter");
    await animationFrame();
    expect(`.o_searchview_input_container .o_facet_values`).toHaveText("a");
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "ilike", "a"]]);
});

test("select an autocomplete field with `context` key", async () => {
    let updateCount = 0;
    class TestComponent extends Component {
        static template = xml`<SearchBar/>`;
        static components = { SearchBar };
        static props = ["*"];
        setup() {
            onWillUpdateProps(() => {
                updateCount++;
            });
        }
    }

    const searchBar = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    // 'r' key to filter on bar "First Record"
    await editSearch("record");
    keyDown("ArrowDown");
    keyDown("ArrowRight");
    await animationFrame();
    keyDown("ArrowDown");
    keyDown("Enter");
    await animationFrame();
    expect(getFacetTexts().map((str) => str.replace(/\s+/g, " "))).toEqual(["Bar First record"]);
    expect(updateCount).toBe(1);
    expect(searchBar.env.searchModel.domain).toEqual([["bar", "=", 1]]);
    expect(searchBar.env.searchModel.context.bar).toEqual([1]);

    // 'r' key to filter on bar "Second Record"
    await editSearch("record");
    keyDown("ArrowDown");
    keyDown("ArrowRight");
    await animationFrame();
    keyDown("ArrowDown");
    keyDown("ArrowDown");
    keyDown("Enter");
    await animationFrame();
    expect(getFacetTexts().map((str) => str.replace(/\s+/g, " "))).toEqual([
        "Bar First record or Second record",
    ]);
    expect(updateCount).toBe(2);
    expect(searchBar.env.searchModel.domain).toEqual(["|", ["bar", "=", 1], ["bar", "=", 2]]);
    expect(searchBar.env.searchModel.context.bar).toEqual([1, 2]);
});

test.tags`desktop`("no search text triggers a reload", async () => {
    let updateCount = 0;
    class TestComponent extends Component {
        static template = xml`<SearchBar/>`;
        static components = { SearchBar };
        static props = ["*"];
        setup() {
            onWillUpdateProps(() => {
                updateCount++;
            });
        }
    }

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });
    keyDown("Enter");
    await animationFrame();
    expect(`.o_searchview_facet_label`).toHaveCount(0);
    expect(updateCount).toBe(1);
});

test("selecting (no result) triggers a search bar rendering", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="bar"/>
            </search>
        `,
    });

    await editSearch("hello there");

    // 'a' key to filter nothing on bar
    keyDown("ArrowRight");
    await animationFrame();
    keyDown("ArrowDown");
    await animationFrame();
    expect(`.o_searchview_autocomplete .focus`).toHaveText("(no result)");

    keyDown("Enter");
    await animationFrame();
    expect(`.o_searchview_facet_label`).toHaveCount(0);
    expect(`.o_searchview input`).toHaveValue("");
});

test("update suggested filters in autocomplete menu with Japanese IME", async () => {
    // The goal here is to simulate as many events happening during an IME
    // assisted composition session as possible. Some of these events are
    // not handled but are triggered to ensure they do not interfere.
    const TEST = "TEST";
    const テスト = "テスト";

    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    // Simulate typing "TEST" on search view.
    await contains(`.o_searchview input`).edit(TEST, { composition: true, confirm: false });
    expect(`.o_searchview_autocomplete`).toHaveCount(1);
    expect(queryFirst`.o_searchview_autocomplete li`).toHaveText("Search Foo for: TEST");

    // Simulate soft-selection of another suggestion from IME through keyboard navigation.
    await contains(`.o_searchview input`).edit(テスト, { composition: true, confirm: false });
    expect(queryFirst`.o_searchview_autocomplete li`).toHaveText("Search Foo for: テスト");

    // Simulate selection on suggestion item "TEST" from IME.
    await contains(`.o_searchview input`).edit(TEST, { composition: true, confirm: false });
    expect(`.o_searchview_autocomplete`).toHaveCount(1);
    expect(queryFirst`.o_searchview_autocomplete li`).toHaveText("Search Foo for: TEST");
});

test("open search view autocomplete on paste value using mouse", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    // Simulate paste text through the mouse.
    navigator.clipboard.writeTextSync("ABC");
    pointerDown(".o_searchview input");
    press("ctrl+v");
    await animationFrame();
    expect(`.o_searchview_autocomplete`).toHaveCount(1);
});

test("select autocompleted many2one", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
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
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("rec");
    await contains(".o_searchview_autocomplete li:last-child").click();
    expect(searchBar.env.searchModel.domain).toEqual([["bar", "child_of", "rec"]]);

    await removeFacet("Bar rec");
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("rec");
    await contains(".o_expand").click();
    await contains(".o_searchview_autocomplete li.o_menu_item.o_indent").click();
    expect(searchBar.env.searchModel.domain).toEqual([["bar", "child_of", 1]]);
});

test(`"null" as autocomplete value`, async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("null");
    expect(`.o_searchview_autocomplete .focus`).toHaveText("Search Foo for: null");

    await contains(".o_searchview_autocomplete li.focus a").click();
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "ilike", "null"]]);
});

test("autocompletion with a boolean field", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="bool"/>
            </search>
        `,
    });
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("y");
    expect(`.o_searchview_autocomplete li`).toHaveCount(1);
    expect(`.o_searchview_autocomplete li:last-child`).toHaveText("Search Bool for: Yes");

    // select "Yes"
    await contains(".o_searchview_autocomplete li:last-child").click();
    expect(searchBar.env.searchModel.domain).toEqual([["bool", "=", true]]);

    await removeFacet("Bool Yes");
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("No");
    expect(`.o_searchview_autocomplete li`).toHaveCount(1);
    expect(`.o_searchview_autocomplete li:last-child`).toHaveText("Search Bool for: No");

    // select "No"
    await contains(".o_searchview_autocomplete li:last-child").click();
    expect(searchBar.env.searchModel.domain).toEqual([["bool", "=", false]]);
});

test("the search value is trimmed to remove unnecessary spaces", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="foo" filter_domain="[('foo', 'ilike', self)]"/>
            </search>
        `,
    });
    await editSearch("bar");
    await validateSearch();
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "ilike", "bar"]]);

    await removeFacet("Foo bar");
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("   bar ");
    await validateSearch();
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "ilike", "bar"]]);
});

test("reference fields are supported in search view", async () => {
    Partner._fields.ref = fields.Reference({ selection: [["partner", "Partner"]] });

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="ref"/>
            </search>
        `,
    });
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("ref");
    await validateSearch();
    expect(searchBar.env.searchModel.domain).toEqual([["ref", "ilike", "ref"]]);

    await removeFacet("Ref ref");
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("ref002");
    await validateSearch();
    expect(searchBar.env.searchModel.domain).toEqual([["ref", "ilike", "ref002"]]);
});

test("expand an asynchronous menu and change the selected item with the mouse during expansion", async () => {
    const def = new Deferred();
    onRpc("name_search", () => def);
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="bar" operator="child_of"/>
            </search>
        `,
    });
    await editSearch("rec");
    await contains(`.o_expand`).click();
    await contains(`.o_searchview_autocomplete li.o_menu_item:first-child`).hover();
    expect(`.o_searchview_autocomplete li.o_menu_item.o_indent`).toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(`.o_searchview_autocomplete li.o_menu_item.o_indent`).toHaveCount(5);
});

test("expand an asynchronous menu and change the selected item with the arrow during expansion", async () => {
    const def = new Deferred();
    onRpc("name_search", () => def);
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="bar" operator="child_of"/>
            </search>
        `,
    });
    await editSearch("rec");
    await contains(".o_expand").click();
    keyDown("ArrowDown");
    await animationFrame();
    expect(`.o_searchview_autocomplete li.o_menu_item.o_indent`).toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(`.o_searchview_autocomplete li.o_menu_item.o_indent`).toHaveCount(5);
});

test("checks that an arrowDown always selects an item", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="bar" operator="child_of"/>
            </search>
        `,
    });
    await editSearch("rec");
    await contains(".o_expand").click();
    click(".o_expand"); // no wait
    hover(`.o_searchview_autocomplete li.o_menu_item.o_indent:last-child`);
    keyDown("ArrowDown");
    await animationFrame();
    expect(".focus").toHaveCount(1);
});

test("checks that an arrowUp always selects an item", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="bar" operator="child_of"/>
            </search>
        `,
    });
    await editSearch("rec");
    await contains(".o_expand").click();
    click(".o_expand"); // no wait
    hover(`.o_searchview_autocomplete li.o_menu_item.o_indent:last-child`);
    keyDown("ArrowUp");
    await animationFrame();
    expect(".focus").toHaveCount(1);
});

test("many2one_reference fields are supported in search view", async () => {
    Partner._fields.res_id = fields.Many2oneReference({
        string: "Resource ID",
        model_field: "bar",
        relation: "partner",
    });

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: /*xml*/ `
            <search>
                <field name="foo" />
                <field name="res_id" />
            </search>
        `,
    });

    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("12");
    expect(queryAllTexts`.o_searchview ul li.dropdown-item`).toEqual([
        "Search Foo for: 12",
        "Search Resource ID for: 12",
    ]);

    keyDown("ArrowDown");
    await validateSearch();
    expect(searchBar.env.searchModel.domain).toEqual([["res_id", "=", 12]]);

    await removeFacet("Resource ID 12");
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("1a");
    expect(queryAllTexts`.o_searchview ul li.dropdown-item`).toEqual(["Search Foo for: 1a"]);

    await validateSearch();
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "ilike", "1a"]]);
});

test("check kwargs of a rpc call with a domain", async () => {
    onRpc("name_search", (_, args) => {
        expect(args).toEqual({
            model: "partner",
            method: "name_search",
            args: [],
            kwargs: {
                args: [["bool", "=", true]],
                context: { lang: "en", uid: 7, tz: "taht", allowed_company_ids: [1] },
                limit: 8,
                name: "F",
            },
        });
    });

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    await editSearch("F");
    expect(`.o_searchview_autocomplete li`).toHaveCount(3);

    keyDown("ArrowDown");
    keyDown("ArrowDown");
    keyDown("ArrowRight");
    await animationFrame();
    keyDown("ArrowDown");
    keyDown("ArrowDown");
    keyDown("ArrowDown");
    keyDown("Enter");
    await animationFrame();
    expect(searchBar.env.searchModel.domain).toEqual([["company", "=", 5]]);
});

test("should wait label promises for one2many search defaults", async () => {
    const def = new Deferred();
    onRpc("read", () => def);

    mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        context: { search_default_company: 1 },
    });
    expect(`.o_cp_searchview`).toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(`.o_cp_searchview`).toHaveCount(1);
    expect(getFacetTexts()[0].replace("\n", "")).toBe("CompanyFirst record");
});

test("globalContext keys in name_search", async () => {
    onRpc("name_search", (_, { kwargs }) => {
        expect.step("name_search");
        expect(kwargs.context.specialKey).toBe("ABCD");
    });

    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="company"/>
            </search>
        `,
        context: { specialKey: "ABCD" },
    });
    await editSearch("F");
    keyDown("ArrowRight");
    await animationFrame();
    expect(["name_search"]).toVerifySteps();
});

test("search a property", async () => {
    onRpc("web_search_read", (_, { kwargs }) => {
        if (kwargs.specification.display_name && kwargs.specification.child_properties) {
            const definition1 = [
                {
                    type: "many2one",
                    string: "My Partner",
                    name: "my_partner",
                    comodel: "partner",
                },
                {
                    type: "many2many",
                    string: "My Partners",
                    name: "my_partners",
                    comodel: "partner",
                },
                {
                    type: "selection",
                    string: "My Selection",
                    name: "my_selection",
                    selection: [
                        ["a", "A"],
                        ["b", "B"],
                        ["c", "C"],
                        ["aa", "AA"],
                    ],
                },
                {
                    type: "tags",
                    string: "My Tags",
                    name: "my_tags",
                    tags: [
                        ["a", "A", 1],
                        ["b", "B", 5],
                        ["c", "C", 3],
                        ["aa", "AA", 2],
                    ],
                },
            ];

            const definition2 = [
                {
                    type: "char",
                    string: "My Text",
                    name: "my_text",
                },
            ];

            return {
                records: [
                    { id: 1, display_name: "Bar 1", child_properties: definition1 },
                    { id: 2, display_name: "Bar 2", child_properties: definition2 },
                ],
            };
        }
    });
    onRpc("name_search", (_, { kwargs }) => {
        if (kwargs.name === "Bo") {
            return [
                [5, "Bob"],
                [6, "Bobby"],
            ];
        } else if (kwargs.name === "Ali") {
            return [
                [9, "Alice"],
                [10, "Alicia"],
            ];
        }
    });

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="properties"/>
            </search>
        `,
    });

    // expand the properties field
    await editSearch("a");
    await contains(".o_expand").click();

    expect(`.o_searchview_input_container li`).toHaveCount(8);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Selection (Bar 1) for: A",
        "My Selection (Bar 1) for: AA",
        "My Tags (Bar 1) for: A",
        "My Tags (Bar 1) for: AA",
        "My Text (Bar 2) for: a",
    ]);

    // click again on the expand icon to hide the properties
    await contains(".o_expand").click();
    expect(`.o_searchview_input_container li`).toHaveCount(1);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual(["Search Properties"]);

    // search for a partner, and expand the many2many property
    click(`.o_searchview_input`);
    clear();
    await editSearch("Bo");
    await contains(".o_expand").click();
    await contains("li:nth-child(3) .o_expand").click();
    expect(`.o_searchview_input_container li`).toHaveCount(6);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "Bob",
        "Bobby",
        "My Text (Bar 2) for: Bo",
    ]);

    // fold all the properties (included the search result)
    await contains(".o_expand").click();
    expect(`.o_searchview_input_container li`).toHaveCount(1);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual(["Search Properties"]);

    // unfold all the properties but fold the search result
    await contains(".o_expand").click();
    await contains("li:nth-child(3) .o_expand").click();
    expect(`.o_searchview_input_container li`).toHaveCount(4);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Text (Bar 2) for: Bo",
    ]);

    // select Bobby
    await contains("li:nth-child(3) .o_expand").click();
    await contains(".o_searchview_input_container li:nth-child(5)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["bar", "=", 1],
        ["properties.my_partners", "in", 6],
    ]);

    // expand the selection properties
    await contains(".o_cp_searchview").click();
    await editSearch("a");
    await contains(".o_expand").click();
    expect(`.o_searchview_input_container li`).toHaveCount(8);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Selection (Bar 1) for: A",
        "My Selection (Bar 1) for: AA",
        "My Tags (Bar 1) for: A",
        "My Tags (Bar 1) for: AA",
        "My Text (Bar 2) for: a",
    ]);

    // select the selection option "AA"
    await contains(".o_searchview_input_container li:nth-child(5)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        "&",
        ["bar", "=", 1],
        ["properties.my_partners", "in", 6],
        "&",
        ["bar", "=", 1],
        ["properties.my_selection", "=", "aa"],
    ]);

    // select the selection option "A"
    await contains(".o_cp_searchview").click();
    await editSearch("a");
    await contains(".o_expand").click();
    await contains(".o_searchview_input_container li:nth-child(4)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        "&",
        ["bar", "=", 1],
        ["properties.my_partners", "in", 6],
        "|",
        "&",
        ["bar", "=", 1],
        ["properties.my_selection", "=", "aa"],
        "&",
        ["bar", "=", 1],
        ["properties.my_selection", "=", "a"],
    ]);

    // reset the search
    await contains(".o_facet_remove").click();
    await contains(".o_facet_remove").click();

    // search a many2one value
    await contains(".o_cp_searchview").click();
    await editSearch("Ali");
    await contains(".o_expand").click();
    await contains("li:nth-child(2) .o_expand").click();
    expect(`.o_searchview_input_container li`).toHaveCount(6);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "Alice",
        "Alicia",
        "My Partners (Bar 1)",
        "My Text (Bar 2) for: Ali",
    ]);
    await contains(".o_searchview_input_container li:nth-child(4)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["bar", "=", 1],
        ["properties.my_partner", "=", 10],
    ]);

    // search a tag value
    await contains(".o_cp_searchview").click();
    await editSearch("A");
    await contains(".o_expand").click();
    expect(`.o_searchview_input_container li`).toHaveCount(8);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Selection (Bar 1) for: A",
        "My Selection (Bar 1) for: AA",
        "My Tags (Bar 1) for: A",
        "My Tags (Bar 1) for: AA",
        "My Text (Bar 2) for: A",
    ]);

    await contains(".o_searchview_input_container li:nth-child(7)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        "&",
        ["bar", "=", 1],
        ["properties.my_partner", "=", 10],
        "&",
        ["bar", "=", 1],
        ["properties.my_tags", "in", "aa"],
    ]);
    // add the tag "B"
    await contains(".o_cp_searchview").click();
    await editSearch("B");
    await contains(".o_expand").click();
    expect(`.o_searchview_input_container li`).toHaveCount(6);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Selection (Bar 1) for: B",
        "My Tags (Bar 1) for: B",
        "My Text (Bar 2) for: B",
    ]);
    await contains(".o_searchview_input_container li:nth-child(5)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        "&",
        ["bar", "=", 1],
        ["properties.my_partner", "=", 10],
        "|",
        "&",
        ["bar", "=", 1],
        ["properties.my_tags", "in", "aa"],
        "&",
        ["bar", "=", 1],
        ["properties.my_tags", "in", "b"],
    ]);

    // try to click on the many2one properties without unfolding
    // it should not add the domain, but unfold the item
    await editSearch("Bobby");
    await contains(".o_expand").click();
    await contains(".o_searchview_input_container li:nth-child(2)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        "&",
        ["bar", "=", 1],
        ["properties.my_partner", "=", 10],
        "|",
        "&",
        ["bar", "=", 1],
        ["properties.my_tags", "in", "aa"],
        "&",
        ["bar", "=", 1],
        ["properties.my_tags", "in", "b"],
    ]);
    expect(`.o_searchview_input_container li`).toHaveCount(5);
    expect(queryAllTexts`.o_searchview_input_container li`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "(no result)",
        "My Partners (Bar 1)",
        "My Text (Bar 2) for: Bobby",
    ]);

    // test the navigation with keyboard
    click(`.o_searchview_input`);
    clear();
    await editSearch("Bo");
    expect(`.o_menu_item.focus`).toHaveText("Search Properties");
    // unfold the properties field
    keyDown("ArrowRight");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("Search Properties");
    expect(queryAll(".fa-caret-down", { root: queryOne`.o_menu_item.focus` })).toHaveCount(1);
    // move on the many2one property
    keyDown("ArrowRight");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("My Partner (Bar 1)");
    expect(queryAll(".fa-caret-right", { root: queryOne`.o_menu_item.focus` })).toHaveCount(1);
    // move on the many2many property
    keyDown("ArrowDown");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("My Partners (Bar 1)");
    expect(queryAll(".fa-caret-right", { root: queryOne`.o_menu_item.focus` })).toHaveCount(1);
    // move on the many2one property again
    keyDown("ArrowUp");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("My Partner (Bar 1)");
    expect(queryAll(".fa-caret-right", { root: queryOne`.o_menu_item.focus` })).toHaveCount(1);
    // unfold the many2one
    keyDown("ArrowRight");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("My Partner (Bar 1)");
    expect(queryAll(".fa-caret-down", { root: queryOne`.o_menu_item.focus` })).toHaveCount(1);
    // select the first many2one
    keyDown("ArrowRight");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("Bob");
    // go up on the parent
    keyDown("ArrowLeft");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("My Partner (Bar 1)");
    expect(queryAll(".fa-caret-down", { root: queryOne`.o_menu_item.focus` })).toHaveCount(1);
    // fold the parent
    keyDown("ArrowLeft");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("My Partner (Bar 1)");
    expect(queryAll(".fa-caret-right", { root: queryOne`.o_menu_item.focus` })).toHaveCount(1);
    // go up on the properties field
    keyDown("ArrowLeft");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("Search Properties");
    expect(queryAll(".fa-caret-down", { root: queryOne`.o_menu_item.focus` })).toHaveCount(1);
    // fold the properties field
    keyDown("ArrowLeft");
    await animationFrame();
    expect(`.o_menu_item.focus`).toHaveText("Search Properties");
    expect(queryAll(".fa-caret-right", { root: queryOne`.o_menu_item.focus` })).toHaveCount(1);
});

test("search a property: definition record id in the context", async () => {
    onRpc("web_search_read", (_, { kwargs }) => {
        if (kwargs.specification.display_name && kwargs.specification.child_properties) {
            expect.step("web_search_read");
            expect(kwargs.domain).toEqual(["&", ["child_properties", "!=", false], ["id", "=", 2]]);

            const definition2 = [
                {
                    type: "char",
                    string: "My Text",
                    name: "my_text",
                },
            ];

            return {
                records: [{ id: 2, display_name: "Bar 2", child_properties: definition2 }],
            };
        }
    });

    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="properties"/>
            </search>
        `,
        context: { active_id: 2 },
    });

    await contains(".o_cp_searchview").click();
    await editSearch("a");
    await contains(".o_expand").click();
    expect(["web_search_read"]).toVerifySteps();
    expect(`.o_searchview_input_container li`).toHaveCount(2);
    expect(queryAll`.o_searchview_input_container li`[1]).toHaveText("My Text (Bar 2) for: a");
});

test("edit a filter", async () => {
    onRpc("/web/domain/validate", () => true);
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"], // we need it to have facet (see facets getter in search_model)
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="filter" string="Filter" domain="[('birthday', '>=', context_today())]"/>
                <filter name="bool" string="Bool" domain="[]" context="{'group_by': 'bool'}"/>
            </search>
        `,
        context: {
            search_default_filter: true,
            search_default_bool: true,
        },
    });
    expect(getFacetTexts()).toEqual(["Filter", "Bool"]);
    expect(`.o_searchview_facet .o_searchview_facet_label`).toHaveCount(2);
    expect(`.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`).toHaveCount(1);
    expect(`.modal`).toHaveCount(0);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal header`).toHaveText("Modify Condition");
    expect(`.modal .o_domain_selector`).toHaveCount(1);
    expect(SELECTORS.condition).toHaveCount(1);
    expect(queryAllTexts`.modal footer button`).toEqual(["Confirm", "Discard"]);
    expect(getCurrentPath()).toBe("Birthday");
    expect(getCurrentOperator()).toBe(">=");
    expect(getCurrentValue()).toBe("context_today()");
    expect(`.modal footer button`).toBeEnabled();

    await clickOnButtonDeleteNode();
    expect(SELECTORS.condition).toHaveCount(0);
    expect(`.modal footer button`).not.toBeEnabled();

    await contains(`.modal ${SELECTORS.addNewRule}`).click();
    expect(SELECTORS.condition).toHaveCount(1);
    expect(getCurrentPath()).toBe("Id");
    expect(getCurrentOperator()).toBe("=");
    expect(getCurrentValue()).toBe("1");

    await contains(".modal footer button").click();
    expect(`.modal`).toHaveCount(0);
    expect(getFacetTexts()).toEqual(["Bool", "Id = 1"]);
});

test("edit a filter with context: context is kept after edition", async () => {
    onRpc("/web/domain/validate", () => true);
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="filter" string="Filter"  context="{'specialKey': 'abc'}" domain="[('foo', '=', 'abc')]"/>
            </search>
        `,
        context: {
            search_default_filter: true,
        },
    });
    expect(getFacetTexts()).toEqual(["Filter"]);
    expect(searchBar.env.searchModel.context.specialKey).toBe("abc");

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([`Foo = abc`]);
    expect(searchBar.env.searchModel.context.specialKey).toBe("abc");
});

test("edit a favorite", async () => {
    const irFilters = [
        {
            context: "{ 'some_key': 'some_value', 'group_by': ['bool'] }",
            domain: "[('foo', 'ilike', 'abc')]",
            id: 1,
            is_default: true,
            name: "My favorite",
            sort: "[]",
            user_id: [2, "Mitchell Admin"],
        },
    ];

    onRpc("/web/domain/validate", () => true);
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"], // we need it to have facet (see facets getter in search_model)
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="company" string="Company" domain="[]" context="{'group_by': 'company'}"/>
            </search>
        `,
        irFilters,
    });
    expect(getFacetTexts()).toEqual(["My favorite"]);
    expect(`.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`).toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("Company");
    expect(getFacetTexts()).toEqual(["My favorite", "Company"]);
    expect(`.o_searchview_facet .o_searchview_facet_label`).toHaveCount(2);
    expect(`.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`).toHaveCount(1);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect(`.modal`).toHaveCount(1);
    expect(getCurrentPath()).toBe("Foo");
    expect(getCurrentOperator()).toBe("contains");
    expect(getCurrentValue()).toBe("abc");

    await contains(".modal footer button").click();
    expect(`.modal`).toHaveCount(0);
    expect(getFacetTexts()).toEqual(["Bool\n>\nCompany", "Foo contains abc"]);
});

test("edit a date filter with comparison active", async () => {
    mockDate("2023-04-28T13:40:00");
    onRpc("/web/domain/validate", () => true);

    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["filter", "comparison"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="birthday" string="Birthday" date="birthday"/>
            </search>
        `,
        context: {
            search_default_birthday: true,
        },
    });
    expect(getFacetTexts()).toEqual(["Birthday: April 2023"]);
    expect(`.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`).toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("Birthday: Previous Period");
    expect(getFacetTexts()).toEqual(["Birthday: April 2023", "Birthday: Previous Period"]);
    expect(`.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`).toHaveCount(1);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect(`.modal`).toHaveCount(1);
    expect(SELECTORS.condition).toHaveCount(1);
    expect(getCurrentPath()).toBe("Birthday");
    expect(getCurrentOperator()).toBe("is between");
    expect(queryAllValues`.o_datetime_input`).toEqual(["04/01/2023", "04/30/2023"]);

    await contains(".modal footer button").click();
    expect(`.modal`).toHaveCount(0);
    expect(getFacetTexts()).toEqual([`Birthday is between 04/01/2023 and 04/30/2023`]);
});

test("edit a field", async () => {
    onRpc("/web/domain/validate", () => true);
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="foo"/>
            </search>
        `,
        context: {
            search_default_foo: "abc",
        },
    });
    expect(getFacetTexts()).toEqual(["Foo\nabc"]);
    expect(`.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`).toHaveCount(1);

    await editSearch("def");
    keyDown("ArrowDown");
    keyDown("Enter"); // select
    await animationFrame();
    expect(getFacetTexts()).toEqual(["Foo\nabc\nor\ndef"]);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect(SELECTORS.condition).toHaveCount(2);

    expect(getCurrentPath(0)).toBe("Foo");
    expect(getCurrentOperator(0)).toBe("contains");
    expect(getCurrentValue(0)).toBe("abc");
    expect(getCurrentPath(1)).toBe("Foo");
    expect(getCurrentOperator(1)).toBe("contains");
    expect(getCurrentValue(1)).toBe("def");

    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([`Foo contains abc or Foo contains def`]);
});

test("no rpc for getting display_name for facets if known", async () => {
    onRpc("/web/domain/validate", () => true);
    onRpc("name_search", (_, { kwargs }) => {
        expect.step(JSON.stringify(kwargs.args /** domain */));
    });
    onRpc("*", (route, { method }) => {
        expect.step(method || route);
    });

    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="filter" string="Filter" domain="[('bar', 'in', [])]"/>
            </search>
        `,
        context: {
            search_default_filter: true,
        },
    });
    expect(getFacetTexts()).toEqual(["Filter"]);
    expect([`get_views`]).toVerifySteps();

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect([`fields_get`]).toVerifySteps();

    await contains(".o-autocomplete--input").click();
    expect([`name_search`, `["!",["id","in",[]]]`]).toVerifySteps();

    await contains(".dropdown-menu li").click();
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual(["Bar is in ( First record )"]);
});

test.tags`desktop`("clicking on search input trigger the search menu", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
    });
    await contains(`.o_searchview_input`).click();
    expect(`.o_search_bar_menu`).toHaveCount(1);
});

test("clicking on the searchview icon trigger the search", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
    });
    await editSearch("a");
    await contains(`.o_searchview button`).click();
    expect(`.o_searchview_input_container .o_facet_values`).toHaveText("a");
});

test("select autocompleted many2one with allowed_company_ids domain", async () => {
    // allowed_company_ids is initially set by the company_service
    serverState.companies = [
        ...serverState.companies,
        // company_service only includes existing companies from cids
        {
            id: 5,
            name: "Hierophant",
        },
    ];
    browser.location.search = "cids=1,5";

    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="bar" domain="[('company', 'in', allowed_company_ids)]"/>
            </search>
        `,
    });

    await editSearch("rec");
    await contains(`.o_expand`).click();
    expect(queryAllTexts(`.o_searchview_input_container li`)).toEqual([
        "Search Bar for: rec",
        "Second record",
        "Third record",
    ]);

    serverState.userContext = { allowed_company_ids: [1] };

    await editSearch("rec");
    await contains(`.o_expand`).click();
    expect(queryAllTexts(`.o_searchview_input_container li`)).toEqual([
        "Search Bar for: rec",
        "Second record",
    ]);
});
