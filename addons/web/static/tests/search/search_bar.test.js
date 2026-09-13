// @ts-check

import { expect, test } from "@odoo/hoot";
import {
    clear,
    click,
    edit,
    hover,
    keyDown,
    pointerDown,
    press,
    queryAll,
    queryAllTexts,
    queryFirst,
    runAllTimers,
} from "@odoo/hoot-dom";
import { animationFrame, Deferred, mockTimeZone, mockTouch } from "@odoo/hoot-mock";
import { Component, onWillUpdateProps, xml } from "@odoo/owl";
import {
    addNewRule,
    clickOnButtonDeleteNode,
    editValue,
    getCurrentOperator,
    getCurrentPath,
    getCurrentValue,
    label,
    SELECTORS,
} from "@web/../tests/components/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineActions,
    defineModels,
    defineWebModels,
    editSearch,
    fields,
    getFacetTexts,
    getService,
    models,
    mountWebClient,
    mountWithCleanup,
    mountWithSearch,
    onRpc,
    patchWithCleanup,
    removeFacet,
    selectGroup,
    serverState,
    toggleMenuItem,
    toggleSearchBarMenu,
    validateSearch,
} from "@web/../tests/web_test_helpers";
import { cookie } from "@web/core/browser/cookie";
import { makeLogger } from "@web/core/debug/debug_logger";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
class Partner extends models.Model {
    name = fields.Char();
    bar = fields.Many2one({ relation: "partner" });
    birthday = fields.Date();
    birth_datetime = fields.Datetime({ string: "Birth DateTime" });
    foo = fields.Char();
    bool = fields.Boolean();
    int_field = fields.Integer({ string: "Int" });
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
        list: `<list><field name="foo"/></list>`,
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
        form: `
            <form>
                <field name="foo" />
                <field name="bool" />
            </form>
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
        views: [
            [false, "list"],
            [false, "form"],
        ],
    },
]);

test.tags("desktop");
test("basic rendering", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });
    expect(queryFirst`.o_searchview input`).toBeFocused();
});

test("computeState is null-safe when the input is not rendered", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });
    searchBar.inputRef = { el: null };
    await searchBar.computeState({ query: "First", expanded: [], subItems: [] });
    expect(searchBar.state.query).toBe("First");
});

test.tags("desktop");
test("navigation with facets", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        context: { search_default_date_group_by: 1 },
    });

    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(queryFirst`.o_searchview input`).toBeFocused();

    await keyDown("ArrowLeft");
    await animationFrame();
    expect(queryFirst`.o_searchview .o_searchview_facet`).toBeFocused();

    await keyDown("ArrowRight");
    await animationFrame();
    expect(queryFirst`.o_searchview input`).toBeFocused();
});

test.tags("desktop");
test("navigation with facets (2)", async () => {
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

    await keyDown("ArrowLeft");
    await animationFrame();
    expect(queryFirst`.o_searchview .o_searchview_facet:nth-child(2)`).toBeFocused();

    await keyDown("ArrowLeft");
    await animationFrame();
    expect(queryFirst`.o_searchview .o_searchview_facet:nth-child(1)`).toBeFocused();

    await keyDown("ArrowLeft");
    await animationFrame();
    expect(queryFirst`.o_searchview input`).toBeFocused();

    await keyDown("ArrowRight");
    await animationFrame();
    expect(queryFirst`.o_searchview .o_searchview_facet:nth-child(1)`).toBeFocused();
});

test.tags("desktop");
test("navigation should move forward from search bar filter", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        context: { search_default_date_group_by: 1 },
    });

    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(queryFirst`.o_searchview input`).toBeFocused();

    await keyDown("Tab");
    await animationFrame();
    expect(queryFirst`.o_searchview_dropdown_toggler`).toBeFocused();
});

test.tags("desktop");
test("typing keeps focus in the input while the filter menu is open", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["filter"],
        searchViewId: false,
    });

    await toggleSearchBarMenu();
    expect(`.o_search_bar_menu`).toHaveCount(1);

    queryFirst`.o_searchview input`.focus();
    await edit("a", { confirm: false });
    await animationFrame();
    expect(`.o_search_bar_menu`).toHaveCount(0);
    expect(queryFirst`.o_searchview input`).toBeFocused();
});

test.tags("desktop");
test("navigation should move backward from search bar filter", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        context: { search_default_date_group_by: 1 },
    });

    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(queryFirst`.o_searchview input`).toBeFocused();

    await keyDown("Shift");
    await press("Tab");
    await animationFrame();
    await press("Tab");
    await animationFrame();
    expect(queryFirst`.d-print-none.btn`).toBeFocused();
});

test.tags("mobile");
test("search input is focused when being toggled", async () => {
    class Parent extends Component {
        static template = xml`
            <div>
                <t t-component="searchBarToggler.component" t-props="searchBarToggler.props"/>
                <SearchBar toggler="searchBarToggler"/>
            </div>
        `;
        static components = { SearchBar };
        static props = ["*"];
        setup() {
            this.searchBarToggler = useSearchBarToggler();
        }
    }
    await mountWithSearch(Parent, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });
    expect(".o_searchview input").toHaveCount(0);
    await contains(`button .fa-search`).click();
    expect(".o_searchview input").toHaveCount(1);
    expect(queryFirst`.o_searchview input`).toBeFocused();
});

test.tags("desktop");
test("search input is not focused on larger touch devices", async () => {
    mockTouch(true);
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });
    expect(".o_searchview input").toHaveCount(1);
    expect(".o_searchview input").not.toBeFocused();
});

test("search date and datetime fields. Support of timezones", async () => {
    mockTimeZone(6);

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    await editSearch("07/15/1983");
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("Enter");
    await animationFrame();
    expect(getFacetTexts().map((str) => str.replace(/\s+/g, " "))).toEqual([
        "Birthday 07/15/1983",
    ]);
    expect(searchBar.env.searchModel.domain).toEqual([["birthday", "=", "1983-07-15"]]);

    await click(`.o_searchview_facet .o_facet_remove`);
    await animationFrame();

    await editSearch("07/15/1983 00:00:00");
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("Enter");
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

    await mountWithCleanup(`<input id="foo"/>`);

    expect(`.o_searchview_autocomplete`).toHaveCount(0);

    await editSearch("Hello there");
    expect(`.o_searchview input`).toHaveValue("Hello there");
    expect(`.o_searchview_autocomplete`).toHaveCount(1);

    await keyDown("Escape");
    await animationFrame();
    expect(`.o_searchview input`).toHaveValue("");
    expect(`.o_searchview_autocomplete`).toHaveCount(0);

    await editSearch("General Kenobi");
    expect(`.o_searchview input`).toHaveValue("General Kenobi");
    expect(`.o_searchview_autocomplete`).toHaveCount(1);

    await click(`input#foo`);
    await animationFrame();
    await runAllTimers();
    expect(`.o_searchview input`).toHaveValue("");
    expect(`.o_searchview_autocomplete`).toHaveCount(0);
    expect("input#foo").toBeFocused();
});

test("select an autocomplete field", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    await editSearch("a");
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(4);

    await keyDown("Enter");
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

    await editSearch("record");
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("ArrowRight");
    await animationFrame();
    await runAllTimers();
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("Enter");
    await animationFrame();
    expect(getFacetTexts().map((str) => str.replace(/\s+/g, " "))).toEqual([
        "Bar First record",
    ]);
    expect(updateCount).toBe(1);
    expect(searchBar.env.searchModel.domain).toEqual([["bar", "=", 1]]);
    expect(searchBar.env.searchModel.context.bar).toEqual([1]);

    await editSearch("record");
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("ArrowRight");
    await animationFrame();
    await runAllTimers();
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("Enter");
    await animationFrame();
    expect(getFacetTexts().map((str) => str.replace(/\s+/g, " "))).toEqual([
        "Bar First record or Second record",
    ]);
    expect(updateCount).toBe(2);
    expect(searchBar.env.searchModel.domain).toEqual([
        "|",
        ["bar", "=", 1],
        ["bar", "=", 2],
    ]);
    expect(searchBar.env.searchModel.context.bar).toEqual([1, 2]);
});

test.tags("desktop");
test("no search text triggers a reload", async () => {
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
    await keyDown("Enter");
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

    await keyDown("ArrowRight");
    await animationFrame();
    await runAllTimers();
    await keyDown("ArrowDown");
    await animationFrame();
    expect(`.o_searchview_autocomplete .focus`).toHaveText("(no result)");

    await keyDown("Enter");
    await animationFrame();
    expect(`.o_searchview_facet_label`).toHaveCount(0);
    expect(`.o_searchview input`).toHaveValue("");
});

test("update suggested filters in autocomplete menu with Japanese IME", async () => {
    const TEST = "TEST";
    const TEST_JP = "テスト";

    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    await click(".o_searchview input");

    await edit(TEST, { composition: true });
    await animationFrame();
    expect(`.o_searchview_autocomplete`).toHaveCount(1);
    expect(`.o_searchview_autocomplete .o-dropdown-item:first`).toHaveText(
        `Search Foo for: ${TEST}`,
    );

    await edit(TEST_JP, { composition: true });
    await animationFrame();
    expect(`.o_searchview_autocomplete .o-dropdown-item:first`).toHaveText(
        `Search Foo for: ${TEST_JP}`,
    );

    await edit(TEST, { composition: true });
    await animationFrame();
    expect(`.o_searchview_autocomplete`).toHaveCount(1);
    expect(queryFirst`.o_searchview_autocomplete .o-dropdown-item`).toHaveText(
        `Search Foo for: ${TEST}`,
    );
});

test("open search view autocomplete on paste value using mouse", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    await navigator.clipboard.writeText("ABC");
    await pointerDown(".o_searchview input");
    await press(["ctrl", "v"]);
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
    await contains(
        ".o_searchview_autocomplete .o-dropdown-item:nth-last-child(2)",
    ).click();
    expect(searchBar.env.searchModel.domain).toEqual([["bar", "child_of", "rec"]]);

    await removeFacet("Bar rec");
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("rec");
    await contains(".o_expand").click();
    await contains(".o_searchview_autocomplete .o-dropdown-item.o_indent").click();
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

    await contains(".o_searchview_autocomplete .o-dropdown-item.focus a").click();
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
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(2);
    expect(`.o_searchview_autocomplete .o-dropdown-item:nth-last-child(2)`).toHaveText(
        "Search Bool for: Yes",
    );

    await contains(
        ".o_searchview_autocomplete .o-dropdown-item:nth-last-child(2)",
    ).click();
    expect(searchBar.env.searchModel.domain).toEqual([["bool", "=", true]]);

    await removeFacet("Bool Yes");
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("No");
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(2);
    expect(`.o_searchview_autocomplete .o-dropdown-item:nth-last-child(2)`).toHaveText(
        "Search Bool for: No",
    );

    await contains(
        ".o_searchview_autocomplete .o-dropdown-item:nth-last-child(2)",
    ).click();
    expect(searchBar.env.searchModel.domain).toEqual([["bool", "=", false]]);
});

test("autocompletion with a selection field", async () => {
    Partner._fields.selection_field = fields.Selection({
        string: "Selection Field",
        selection: [
            ["abc", "ABC"],
            ["aef", "AEF"],
            ["ghi", "GHI"],
        ],
    });
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="selection_field"/>
            </search>
        `,
    });
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("a");
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(2);
    expect(`.o_searchview_autocomplete .o-dropdown-item:first`).toHaveText(
        "Search Selection Field for: a",
    );
    await contains(".o_searchview_autocomplete .o-dropdown-item:first").click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(4);
    expect(`.o_searchview_autocomplete .o-dropdown-item:eq(1)`).toHaveText("ABC");
    expect(`.o_searchview_autocomplete .o-dropdown-item:eq(2)`).toHaveText("AEF");
    await contains(`.o_searchview_autocomplete .o-dropdown-item:eq(2)`).click();
    expect(searchBar.env.searchModel.domain).toEqual([["selection_field", "=", "aef"]]);

    await removeFacet("Selection Field AEF");
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("h");
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(2);
    expect(`.o_searchview_autocomplete .o-dropdown-item:first`).toHaveText(
        "Search Selection Field for: h",
    );
    await contains(".o_searchview_autocomplete .o-dropdown-item:first").click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(3);
    expect(`.o_searchview_autocomplete .o-dropdown-item:eq(1)`).toHaveText("GHI");

    await contains(`.o_searchview_autocomplete .o-dropdown-item:eq(1)`).click();
    expect(searchBar.env.searchModel.domain).toEqual([["selection_field", "=", "ghi"]]);
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
    await contains(`.o_searchview_autocomplete .o-dropdown-item:first-child`).hover();
    expect(`.o_searchview_autocomplete .o-dropdown-item.o_indent`).toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(`.o_searchview_autocomplete .o-dropdown-item.o_indent`).toHaveCount(5);
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
    await keyDown("ArrowDown");
    await animationFrame();
    expect(`.o_searchview_autocomplete .o-dropdown-item.o_indent`).toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(`.o_searchview_autocomplete .o-dropdown-item.o_indent`).toHaveCount(5);
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
    await hover(`.o_searchview_autocomplete .o-dropdown-item.o_indent:last`);
    await contains(".o_expand").click();
    await keyDown("ArrowDown");
    expect(".o_searchview_autocomplete .focus").toHaveCount(1);
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
    await hover(`.o_searchview_autocomplete .o-dropdown-item.o_indent:last`);
    await contains(".o_expand").click();
    await keyDown("ArrowUp");
    expect(".o_searchview_autocomplete .focus").toHaveCount(1);
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
        searchViewArch: `
            <search>
                <field name="foo" />
                <field name="res_id" />
            </search>
        `,
    });

    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("12");
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Foo for: 12",
        "Search Resource ID for: 12",
        "Custom Filter...",
    ]);

    await keyDown("ArrowDown");
    await validateSearch();
    expect(searchBar.env.searchModel.domain).toEqual([["res_id", "=", 12]]);

    await removeFacet("Resource ID 12");
    expect(searchBar.env.searchModel.domain).toEqual([]);

    await editSearch("1a");
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Foo for: 1a",
        "Custom Filter...",
    ]);

    await validateSearch();
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "ilike", "1a"]]);
});

test("check kwargs of a rpc call with a domain", async () => {
    onRpc("name_search", (params) => {
        expect(params).toMatchObject({
            model: "partner",
            method: "name_search",
            args: [],
            kwargs: {
                domain: [["bool", "=", true]],
                limit: 8 + 1,
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
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(4);

    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("ArrowRight");
    await animationFrame();
    await runAllTimers();
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("ArrowDown");
    await animationFrame();
    await keyDown("Enter");
    await animationFrame();
    expect(searchBar.env.searchModel.domain).toEqual([["company", "=", 5]]);
});

test("should wait label promises for many2one search defaults", async () => {
    const def = new Deferred();
    onRpc("read", () => def);

    const mounted = mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        context: { search_default_company: 1 },
    });
    await animationFrame();
    expect(`.o_cp_searchview`).toHaveCount(0);

    def.resolve();
    await mounted;
    await animationFrame();
    expect(`.o_cp_searchview`).toHaveCount(1);
    expect(getFacetTexts()[0].replace("\n", "")).toBe("CompanyFirst record");
});

test("should wait label promises for many2many search defaults", async () => {
    Partner._fields.m2m = fields.Many2many({ relation: "partner" });
    const def = new Deferred();
    onRpc("read", () => def);

    const mounted = mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="m2m"/>
            </search>
        `,
        context: { search_default_m2m: [1, 2] },
    });
    await animationFrame();
    expect(`.o_cp_searchview`).toHaveCount(0);

    def.resolve();
    await mounted;
    await animationFrame();
    expect(`.o_cp_searchview`).toHaveCount(1);
    expect(getFacetTexts()[0].replace("\n", "")).toBe(
        "M2mFirst record or Second record",
    );
});

test("many2one search default on a missing record does not crash the view", async () => {
    onRpc("read", ({ args }) => {
        expect.step(`read ${args[0]}`);
    });

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        context: { search_default_company: 42 },
    });
    expect.verifySteps(["read 42"]);
    expect(`.o_cp_searchview`).toHaveCount(1);
    expect(getFacetTexts()[0].replace("\n", "")).toBe("Company42");
    expect(searchBar.env.searchModel.domain).toEqual([["company", "=", 42]]);
});

test("invalid selection search default does not crash the view", async () => {
    Partner._fields.selection_field = fields.Selection({
        string: "Selection Field",
        selection: [
            ["abc", "ABC"],
            ["def", "DEF"],
        ],
    });

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="selection_field"/>
            </search>
        `,
        context: { search_default_selection_field: "ghi" },
    });
    expect(`.o_cp_searchview`).toHaveCount(1);
    expect(getFacetTexts()[0].replace("\n", "")).toBe("Selection Fieldghi");
    expect(searchBar.env.searchModel.domain).toEqual([["selection_field", "=", "ghi"]]);
});

test("globalContext keys in name_search", async () => {
    onRpc("name_search", ({ kwargs }) => {
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
    await keyDown("ArrowRight");
    await animationFrame();
    expect.verifySteps(["name_search"]);
});

test("search a property", async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        if (
            kwargs.specification.display_name &&
            kwargs.specification.child_properties
        ) {
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
    onRpc("name_search", ({ kwargs }) => {
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

    await editSearch("a");
    await contains(".o_expand").click();

    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Selection (Bar 1) for: A",
        "My Selection (Bar 1) for: AA",
        "My Tags (Bar 1) for: A",
        "My Tags (Bar 1) for: AA",
        "My Text (Bar 2) for: a",
        "Custom Filter...",
    ]);

    await contains(".o_expand").click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(2);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "Custom Filter...",
    ]);

    await contains(`.o_searchview_input`).clear();
    await editSearch("Bo");
    await contains(".o_expand").click();
    await contains(
        ".o_searchview_autocomplete .o-dropdown-item:nth-child(3) .o_expand",
    ).click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(7);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "Bob",
        "Bobby",
        "My Text (Bar 2) for: Bo",
        "Custom Filter...",
    ]);

    await contains(".o_expand").click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(2);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "Custom Filter...",
    ]);

    await contains(".o_expand").click();
    await contains(
        ".o_searchview_autocomplete .o-dropdown-item:nth-child(3) .o_expand",
    ).click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(5);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Text (Bar 2) for: Bo",
        "Custom Filter...",
    ]);

    await contains(
        ".o_searchview_autocomplete .o-dropdown-item:nth-child(3) .o_expand",
    ).click();
    await contains(".o_searchview_autocomplete .o-dropdown-item:nth-child(5)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["bar", "=", 1],
        ["properties.my_partners", "in", 6],
    ]);

    await contains(".o_cp_searchview").click();
    await editSearch("a");
    await contains(".o_expand").click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Selection (Bar 1) for: A",
        "My Selection (Bar 1) for: AA",
        "My Tags (Bar 1) for: A",
        "My Tags (Bar 1) for: AA",
        "My Text (Bar 2) for: a",
        "Custom Filter...",
    ]);

    await contains(".o_searchview_autocomplete .o-dropdown-item:nth-child(5)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        "&",
        ["bar", "=", 1],
        ["properties.my_partners", "in", 6],
        "&",
        ["bar", "=", 1],
        ["properties.my_selection", "=", "aa"],
    ]);

    await contains(".o_cp_searchview").click();
    await editSearch("a");
    await contains(".o_expand").click();
    await contains(".o_searchview_autocomplete .o-dropdown-item:nth-child(4)").click();
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

    await contains(".o_facet_remove").click();
    await contains(".o_facet_remove").click();

    await contains(".o_cp_searchview").click();
    await editSearch("Ali");
    await contains(".o_expand").click();
    await contains(
        ".o_searchview_autocomplete .o-dropdown-item:nth-child(2) .o_expand",
    ).click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(7);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "Alice",
        "Alicia",
        "My Partners (Bar 1)",
        "My Text (Bar 2) for: Ali",
        "Custom Filter...",
    ]);
    await contains(".o_searchview_autocomplete .o-dropdown-item:nth-child(4)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["bar", "=", 1],
        ["properties.my_partner", "=", 10],
    ]);

    await contains(".o_cp_searchview").click();
    await editSearch("A");
    await contains(".o_expand").click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Selection (Bar 1) for: A",
        "My Selection (Bar 1) for: AA",
        "My Tags (Bar 1) for: A",
        "My Tags (Bar 1) for: AA",
        "My Text (Bar 2) for: A",
        "Custom Filter...",
    ]);

    await contains(".o_searchview_autocomplete .o-dropdown-item:nth-child(7)").click();
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        "&",
        ["bar", "=", 1],
        ["properties.my_partner", "=", 10],
        "&",
        ["bar", "=", 1],
        ["properties.my_tags", "in", "aa"],
    ]);
    await contains(".o_cp_searchview").click();
    await editSearch("B");
    await contains(".o_expand").click();
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(7);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "My Partners (Bar 1)",
        "My Selection (Bar 1) for: B",
        "My Tags (Bar 1) for: B",
        "My Text (Bar 2) for: B",
        "Custom Filter...",
    ]);
    await contains(".o_searchview_autocomplete .o-dropdown-item:nth-child(5)").click();
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

    await editSearch("Bobby");
    await contains(".o_expand").click();
    await contains(".o_searchview_autocomplete .o-dropdown-item:nth-child(2)").click();
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
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(6);
    expect(queryAllTexts`.o_searchview_autocomplete .o-dropdown-item`).toEqual([
        "Search Properties",
        "My Partner (Bar 1)",
        "(no result)",
        "My Partners (Bar 1)",
        "My Text (Bar 2) for: Bobby",
        "Custom Filter...",
    ]);

    await contains(`.o_searchview_input`).clear();
    await animationFrame();
    await runAllTimers();

    await editSearch("Bo");
    await animationFrame();
    expect(`.o-dropdown-item.focus`).toHaveText("Search Properties");
    await keyDown("ArrowRight");
    await animationFrame();
    await runAllTimers();
    expect(`.o-dropdown-item.focus`).toHaveText("Search Properties");
    expect(".o-dropdown-item.focus:only .fa-caret-down").toHaveCount(1);
    await keyDown("ArrowRight", { repeat: false });
    await animationFrame();
    await runAllTimers();
    expect(`.o-dropdown-item.focus`).toHaveText("My Partner (Bar 1)");
    expect(".o-dropdown-item.focus:only .fa-caret-right").toHaveCount(1);
    await keyDown("ArrowDown");
    await animationFrame();
    expect(`.o-dropdown-item.focus`).toHaveText("My Partners (Bar 1)");
    expect(".o-dropdown-item.focus:only .fa-caret-right").toHaveCount(1);
    await keyDown("ArrowUp");
    await animationFrame();
    expect(`.o-dropdown-item.focus`).toHaveText("My Partner (Bar 1)");
    expect(".o-dropdown-item.focus:only .fa-caret-right").toHaveCount(1);
    await keyDown("ArrowRight");
    await animationFrame();
    await runAllTimers();
    expect(`.o-dropdown-item.focus`).toHaveText("My Partner (Bar 1)");
    expect(".o-dropdown-item.focus:only .fa-caret-down").toHaveCount(1);
    await keyDown("ArrowRight", { repeat: false });
    await animationFrame();
    await runAllTimers();
    expect(`.o-dropdown-item.focus`).toHaveText("Bob");
    await keyDown("ArrowLeft");
    await animationFrame();
    await runAllTimers();
    expect(`.o-dropdown-item.focus`).toHaveText("My Partner (Bar 1)");
    expect(".o-dropdown-item.focus:only .fa-caret-down").toHaveCount(1);
    await keyDown("ArrowLeft");
    await animationFrame();
    await runAllTimers();
    expect(`.o-dropdown-item.focus`).toHaveText("My Partner (Bar 1)");
    expect(".o-dropdown-item.focus:only .fa-caret-right").toHaveCount(1);
    await keyDown("ArrowLeft");
    await animationFrame();
    await runAllTimers();
    expect(`.o-dropdown-item.focus`).toHaveText("Search Properties");
    expect(".o-dropdown-item.focus:only .fa-caret-down").toHaveCount(1);
    await keyDown("ArrowLeft");
    await animationFrame();
    await runAllTimers();
    expect(`.o-dropdown-item.focus`).toHaveText("Search Properties");
    expect(".o-dropdown-item.focus:only .fa-caret-right").toHaveCount(1);
});

test("search a property: definition record id in the context", async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        if (
            kwargs.specification.display_name &&
            kwargs.specification.child_properties
        ) {
            expect.step("web_search_read");
            expect(kwargs.domain).toEqual([
                "&",
                ["child_properties", "!=", false],
                ["id", "=", 2],
            ]);

            const definition2 = [
                {
                    type: "char",
                    string: "My Text",
                    name: "my_text",
                },
            ];

            return {
                records: [
                    { id: 2, display_name: "Bar 2", child_properties: definition2 },
                ],
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
    expect.verifySteps(["web_search_read"]);
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(3);
    expect(queryAll`.o_searchview_autocomplete .o-dropdown-item`[1]).toHaveText(
        "My Text (Bar 2) for: a",
    );
});

test("edit a filter", async () => {
    onRpc("/web/domain/validate", () => true);
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
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
    expect(
        `.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`,
    ).toHaveCount(1);
    expect(`.modal`).toHaveCount(0);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal header`).toHaveText("Custom Filter");
    expect(`.modal .o_domain_selector`).toHaveCount(1);
    expect(SELECTORS.condition).toHaveCount(1);
    expect(queryAllTexts`.modal footer button`).toEqual(["Search", "Discard"]);
    expect(getCurrentPath()).toBe("Birthday");
    expect(getCurrentOperator()).toBe(label(">="));
    expect(getCurrentValue()).toBe("context_today()");
    expect(`.modal footer button`).toBeEnabled();

    await clickOnButtonDeleteNode();
    expect(SELECTORS.condition).toHaveCount(0);
    expect(`.modal footer button:first`).not.toBeEnabled();

    await contains(`.modal ${SELECTORS.addNewRule}`).click();
    expect(SELECTORS.condition).toHaveCount(1);
    expect(getCurrentPath()).toBe("Id");
    expect(getCurrentOperator()).toBe(label("="));
    expect(getCurrentValue()).toBe("1");

    await contains(".modal footer button").click();
    expect(`.modal`).toHaveCount(0);
    expect(getFacetTexts()).toEqual(["Id = 1", "Bool"]);
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
    await contains(`.modal ${SELECTORS.addNewRule}`).click();
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([`Foo = abc`, `Foo = abc`]);
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
            user_ids: [2],
        },
    ];

    onRpc("/web/domain/validate", () => true);
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="company" string="Company" domain="[]" context="{'group_by': 'company'}"/>
            </search>
        `,
        irFilters,
    });
    expect(getFacetTexts()).toEqual(["My favorite"]);
    expect(
        `.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`,
    ).toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("Company");
    expect(getFacetTexts()).toEqual(["My favorite", "Company"]);
    expect(`.o_searchview_facet .o_searchview_facet_label`).toHaveCount(2);
    expect(
        `.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`,
    ).toHaveCount(1);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect(`.modal`).toHaveCount(1);
    expect(getCurrentPath()).toBe("Foo");
    expect(getCurrentOperator()).toBe("contains");
    expect(getCurrentValue()).toBe("abc");

    await editValue("def");
    expect(getCurrentPath()).toBe("Foo");
    expect(getCurrentOperator()).toBe("contains");
    expect(getCurrentValue()).toBe("def");

    await contains(".modal footer button").click();
    expect(`.modal`).toHaveCount(0);
    expect(getFacetTexts()).toEqual([`Foo ${label("ilike")} def`, "Bool\n>\nCompany"]);
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
    expect(
        `.o_searchview_facet.o_facet_with_domain .o_searchview_facet_label`,
    ).toHaveCount(1);

    await editSearch("def");
    await keyDown("Enter");
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
    expect(getFacetTexts()).toEqual([`Foo\nabc\nor\ndef`]);
});

test("no rpc for getting display_name for facets if known", async () => {
    onRpc("/web/domain/validate", () => true);
    onRpc("web_name_search", ({ kwargs }) => {
        expect.step(kwargs.domain);
    });
    onRpc(({ method }) => method !== "lazy_session_info" && expect.step(method));

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
    expect.verifySteps(["get_views"]);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect.verifySteps(["fields_get"]);

    await contains(".o-autocomplete--input").click();
    expect.verifySteps(["web_name_search", ["!", ["id", "in", []]]]);

    await contains(
        ".o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item",
    ).click();
    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual(["Bar = First record"]);
});

test.tags("desktop");
test("clicking on search input trigger the search menu", async () => {
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

test("facets display with any / not any operator", async function () {
    onRpc(({ method }) => method !== "lazy_session_info" && expect.step(method));
    onRpc("/web/domain/validate", () => {
        expect.step("/web/domain/validate");
        return true;
    });

    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="filter" string="Filter" domain="[('company', 'any', [('bar', 'any', [('company', 'in', ['JD7', 'KDB'])])])]"/>
            </search>
        `,
        context: {
            search_default_filter: true,
        },
    });
    expect(getFacetTexts()).toEqual(["Filter"]);
    expect.verifySteps([`get_views`]);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect.verifySteps([`fields_get`]);

    await addNewRule();

    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([
        "Company : ( Bar : ( Company = ( JD7 or KDB ) and Company = ( JD7 or KDB ) ) )",
    ]);
    expect.verifySteps([`/web/domain/validate`]);
});

test("facets display with any / not any operator (with a complex path)", async function () {
    onRpc(({ method }) => method !== "lazy_session_info" && expect.step(method));
    onRpc("/web/domain/validate", () => {
        expect.step("/web/domain/validate");
        return true;
    });
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="filter" string="Filter" domain="['|', ('company.company', 'any', [('id', '=', 1)]), ('Bar', '=', false)]"/>
            </search>
        `,
        context: {
            search_default_filter: true,
        },
    });
    expect(getFacetTexts()).toEqual(["Filter"]);
    expect.verifySteps([`get_views`]);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect.verifySteps([`fields_get`]);

    await addNewRule();

    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([
        `Company ➔ Company : ( Id = 1 and Id = 1 ) or Bar ${label("not set")}`,
    ]);
    expect.verifySteps([`/web/domain/validate`]);
});

test("facets display with any / not any operator (with a or)", async function () {
    onRpc(({ method }) => method !== "lazy_session_info" && expect.step(method));
    onRpc("/web/domain/validate", () => {
        expect.step("/web/domain/validate");
        return true;
    });
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="filter" string="Filter" domain="['|', ('company', 'any', [('id', '=', 1)]), ('bar', '=', false)]"/>
            </search>
        `,
        context: {
            search_default_filter: true,
        },
    });
    expect(getFacetTexts()).toEqual(["Filter"]);
    expect.verifySteps([`get_views`]);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect.verifySteps([`fields_get`]);

    await addNewRule();

    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([
        `Company : ( Id = 1 and Id = 1 ) or Bar ${label("not set")}`,
    ]);
    expect.verifySteps([`/web/domain/validate`]);
});

test("facets display with any / not any operator (check brackets)", async function () {
    onRpc(({ method }) => method !== "lazy_session_info" && expect.step(method));
    onRpc("/web/domain/validate", () => {
        expect.step("/web/domain/validate");
        return true;
    });
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter isDebugMode="true" name="filter" string="Filter" domain="['|', ('company', 'any', [('bar', 'any', [('bool', '=', False)]), ('bar', 'any', [('bool', '=', True)])]), ('bar', '=', false)]"/>
            </search>
        `,
        context: {
            search_default_filter: true,
        },
    });
    expect(getFacetTexts()).toEqual(["Filter"]);
    expect.verifySteps([`get_views`]);

    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect.verifySteps([`fields_get`]);

    await addNewRule();

    await contains(".modal footer button").click();
    expect(getFacetTexts()).toEqual([
        `Company : ( Bar : ( Bool ${label("not set")} and Bool ${label("not set")} ) and Bar : ( Bool ${label("set")} ) ) or Bar ${label("not set")}`,
    ]);
    expect.verifySteps([`/web/domain/validate`]);
});

test("select autocompleted many2one with allowed_company_ids domain (cids: 1-5)", async () => {
    cookie.set("cids", "1-5");
    serverState.companies = [
        ...serverState.companies,
        {
            id: 5,
            name: "Hierophant",
        },
    ];

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
    expect(queryAllTexts(`.o_searchview_autocomplete .o-dropdown-item`)).toEqual([
        "Search Bar for: rec",
        "Second record",
        "Third record",
        "Custom Filter...",
    ]);
});

test("select autocompleted many2one with allowed_company_ids domain (cids: 1)", async () => {
    cookie.set("cids", "1");
    serverState.companies = [
        ...serverState.companies,
        {
            id: 5,
            name: "Hierophant",
        },
    ];

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

    await click(".o_searchview input");
    await clear();
    await animationFrame();

    await editSearch("rec");
    await contains(`.o_expand`).click();
    await runAllTimers();
    expect(queryAllTexts(`.o_searchview_autocomplete .o-dropdown-item`)).toEqual([
        "Search Bar for: rec",
        "Second record",
        "Custom Filter...",
    ]);
});

test("throw error when domain can not be parsed", async () => {
    expect.errors(1);
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="bar" domain="[('company', 'in', wrong)]"/>
            </search>
        `,
    });

    await editSearch("rec");
    await contains(`.o_expand`).click();
    expect.verifyErrors(["Error: Name 'wrong' is not defined"]);
});

test("dropdown menu last element is 'Custom Filter...'", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="foo"/>
            </search>
        `,
    });
    await editSearch("a");
    await animationFrame();
    expect(".o_searchview_autocomplete .o-dropdown-item:last").toHaveText(
        "Custom Filter...",
    );
});

test("order by count resets when there is no group left", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy", "filter"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="foo" domain="[('foo', '=', 'qsdf')]"/>
            </search>
        `,
    });
    searchBar.env.searchModel.canOrderByCount = true;
    await toggleSearchBarMenu();
    await selectGroup("bool");
    await selectGroup("bar");
    await toggleMenuItem("Foo");
    expect(".fa-sort").toHaveCount(1);
    await contains(".fa-sort", { visible: false }).click();
    expect(".fa-arrow-down-9-1").toHaveCount(1);
    await contains(".fa-arrow-down-9-1").click();
    expect(".fa-arrow-down-1-9").toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("Foo");
    expect(".fa-arrow-down-1-9").toHaveCount(1);

    await toggleMenuItem("Foo");
    await toggleMenuItem("Bool");
    expect(".fa-arrow-down-1-9").toHaveCount(1);
    await toggleMenuItem("Bar");
    expect(".fa-arrow-down-1-9").toHaveCount(0);

    await toggleMenuItem("Bar");
    expect(".fa-arrow-down-1-9").toHaveCount(0);
    expect(".fa-sort").toHaveCount(1);
    await contains(".fa-sort", { visible: false }).click();
    await contains(".fa-arrow-down-9-1").click();
    expect(".fa-arrow-down-1-9").toHaveCount(1);
    await toggleSearchBarMenu();
    await toggleMenuItem("Bool");
    expect(".fa-arrow-down-1-9").toHaveCount(1);

    await contains(".o_facet_remove").click();
    expect(".fa-arrow-down-1-9").toHaveCount(1);
    await contains(".o_facet_remove").click();
    expect(".o_searchview_facet").toHaveCount(0);

    await toggleSearchBarMenu();
    await toggleMenuItem("Bar");
    expect(".fa-arrow-down-1-9").toHaveCount(0);
    expect(".fa-sort").toHaveCount(1);
});

test("subitems have a load more item if there is more records available", async () => {
    for (let i = 0; i < 20; i++) {
        Partner._records.push({
            id: 100 + i,
            name: `Home Depot ${i}`,
        });
    }
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="company"/>
            </search>
        `,
    });
    await editSearch("Home");
    await contains(".o_expand").click();
    await expect(".o_searchview_autocomplete .o-dropdown-item.o_indent").toHaveCount(
        8 + 1,
    );
    await expect(
        ".o_searchview_autocomplete .o-dropdown-item.o_indent:last",
    ).toHaveText("Load more");
    await contains(".o_searchview_autocomplete .o-dropdown-item.o_indent:last").click();
    await expect(".o_searchview_autocomplete .o-dropdown-item.o_indent").toHaveCount(
        8 + 8 + 1,
    );
    await expect(
        ".o_searchview_autocomplete .o-dropdown-item.o_indent:last",
    ).toHaveText("Load more");
});

test("subitems do not have a load more item if there is no more records available", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="company"/>
            </search>
        `,
    });
    await editSearch("home");
    await contains(".o_expand").click();
    await expect(".o_searchview_autocomplete .o-dropdown-item.o_indent").toHaveCount(1);
    await expect(".o_searchview_autocomplete .o-dropdown-item.o_indent").toHaveText(
        "(no result)",
    );
});

test("single name_search call and no flicker when holding ArrowRight", async function () {
    onRpc(({ method }) => {
        if (method === "name_search") {
            expect.step(method);
        }
    });

    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    await editSearch("a");
    await press("arrowdown");
    await press("arrowleft");
    await animationFrame();

    for (let i = 0; i < 3; i++) {
        await press("arrowright", { repeat: i > 0 });
        await animationFrame();
        expect(".o_menu_item.o_indent").toHaveCount(0);
        expect("input.o_searchview_input").toBeFocused();
    }
    await press("arrowright");
    expect.verifySteps(["name_search"]);
});

test.tags("desktop");
test("no crash when search component is destroyed with input", async () => {
    const def = new Deferred();
    onRpc("web_read", () => def);
    defineWebModels();
    await mountWebClient();
    await getService("action").doAction(1);
    expect(".o_list_view").toHaveCount(1);
    await contains(".o_data_cell:eq(0)").click();
    expect(".o_list_view").toHaveCount(1);
    await editSearch("Jethalal");
    def.resolve();
    await animationFrame();
    await runAllTimers();
    expect(".o_form_view").toHaveCount(1);
});

test("search on full query without waiting for display synchronisation", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
    });

    await editSearch("01234");
    expect(".o-dropdown-item:first").toHaveText("Search Foo for: 01234");
    await press("5");
    expect(".o-dropdown-item:first").toHaveText("Search Foo for: 01234");
    await press("6");
    expect(".o-dropdown-item:first").toHaveText("Search Foo for: 01234");
    await keyDown("Enter");
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "ilike", "0123456"]]);
});

test.tags("desktop");
test("typing right after opening the search menu keeps focus in the input", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["filter", "groupBy", "favorite"],
        searchViewId: false,
    });

    await click("input.o_searchview_input");
    await animationFrame();
    expect(".o_search_bar_menu").toHaveCount(1);

    await editSearch("ab");
    await animationFrame();
    expect(".o_search_bar_menu").toHaveCount(0);
    expect("input.o_searchview_input").toBeFocused();
    expect("input.o_searchview_input").toHaveValue("ab");
});

test("a stale expansion must not revert a cleared query", async () => {
    const def = new Deferred();
    onRpc("name_search", () => def);
    const searchBar = await mountWithSearch(SearchBar, {
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
    await editSearch("");
    def.resolve();
    await animationFrame();
    expect(searchBar.state.query).toBe("", {
        message: "a superseded expansion must not revert the cleared query",
    });
});

test("a facet never advertises a value the domain does not use", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="int_field"/>
            </search>
        `,
    });
    await editSearch("5");

    const item = searchBar.items.find((i) => i.fieldType === "integer");
    expect(item.value).toBe(5);

    searchBar.state.query = "5x";
    searchBar.selectItem(item);
    await animationFrame();

    const { label, value } = searchBar.env.searchModel.query.find(
        (q) => q.searchItemId === item.searchItemId,
    ).autocompleteValue;
    expect(value).toBe(5);
    expect(label).toBe("5");
});

test("the custom filter entry is addressable like every other item", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="foo"/>
            </search>
        `,
    });
    await editSearch("a");

    const customFilter = searchBar.items.find((i) => i.isAddCustomFilterButton);
    expect(customFilter.id).toBeOfType("number");
    expect(searchBar.items.find((i) => i.id === customFilter.id)).toBe(customFilter);
    expect(new Set(searchBar.items.map((i) => i.id)).size).toBe(searchBar.items.length);
});

test("a search item with an unevaluatable invisible does not break the menus", async () => {
    patchWithCleanup(console, { warn: () => expect.step("warn") });
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="foo"/>
                <filter name="a" string="A" domain="[]" invisible="no_such_name"/>
                <filter name="b" string="B" domain="[]"/>
            </search>
        `,
    });

    await toggleSearchBarMenu();
    expect(queryAllTexts`.o_filter_menu .o_menu_item`).toEqual([
        "A",
        "B",
        "Custom Filter...",
    ]);

    await editSearch("a");
    expect(`.o_searchview_autocomplete .o-dropdown-item`).toHaveCount(2);
    expect.verifySteps(["warn"]);
});

test("removing a facet keeps the DOM identity of the ones after it", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter name="a" string="A" domain="[('bar','=',1)]"/>
                <separator/>
                <filter name="b" string="B" domain="[('bar','=',2)]"/>
                <separator/>
                <filter name="c" string="C" domain="[('bar','=',3)]"/>
            </search>
        `,
        context: { search_default_a: 1, search_default_b: 1, search_default_c: 1 },
    });
    expect(getFacetTexts()).toEqual(["A", "B", "C"]);

    const facets = queryAll`.o_searchview_facet`;
    const lastFacet = facets.at(-1);
    lastFacet.focus();
    expect(lastFacet).toBeFocused();

    await contains(`.o_searchview_facet:first-child .o_facet_remove`).click();

    expect(getFacetTexts()).toEqual(["B", "C"]);
    expect(queryAll`.o_searchview_facet`.at(-1)).toBe(lastFacet);
});

test("an expanded search item retired mid-flight does not break computeState", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchViewId: false,
        searchViewArch: `
            <search>
                <field name="bar"/>
            </search>
        `,
    });
    const barItem = Object.values(searchBar.env.searchModel.searchItems).find(
        (item) => item.fieldName === "bar",
    );
    await editSearch("a");
    await searchBar.computeState({ expanded: [barItem.id] });
    expect(searchBar.state.expanded).toEqual([barItem.id]);

    delete searchBar.env.searchModel.searchItems[barItem.id];
    await searchBar.computeState({ query: "ab" });

    expect(searchBar.state.expanded).toEqual([]);
    expect(searchBar.state.query).toBe("ab");
});

test("a count-sortable group-by facet label announces itself as a button", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewArch: `<search/>`,
    });
    searchBar.env.searchModel.canOrderByCount = true;
    await toggleSearchBarMenu();
    await selectGroup("bool");

    expect(".o_searchview_facet").toHaveCount(1);
    expect(".o_searchview_facet .o_searchview_facet_label").toHaveAttribute(
        "role",
        "button",
    );
});

test("a plain group-by facet label stays non-interactive", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewArch: `<search/>`,
    });
    searchBar.env.searchModel.canOrderByCount = false;
    await toggleSearchBarMenu();
    await selectGroup("bool");

    expect(".o_searchview_facet .o_searchview_facet_label").toHaveAttribute(
        "role",
        "img",
    );
});

test("a filter facet label carrying a domain announces itself as a button", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="foo" domain="[('foo', '=', 'qsdf')]"/>
            </search>
        `,
        context: { search_default_foo: true },
    });

    expect(".o_searchview_facet .o_searchview_facet_label").toHaveAttribute(
        "role",
        "button",
    );
});

test("facets sit in a list and carry their visible text as accessible name", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["filter"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="foo" domain="[('foo', '=', 'qsdf')]"/>
            </search>
        `,
        context: { search_default_foo: true },
    });

    const facet = queryFirst`.o_searchview_facet`;
    const list = facet.closest("[role='list']");
    expect(list).not.toBe(null);
    expect(facet).toHaveAttribute("aria-label", "Foo");
    expect(".o_facet_remove").toHaveAttribute("aria-label", "Remove Foo");
    expect(getComputedStyle(list).display).toBe("contents");
});

test("a multi-value facet names itself with its separator", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="gb_foo" context="{'group_by': 'foo'}"/>
                <filter string="Bar" name="gb_bar" context="{'group_by': 'bar'}"/>
            </search>
        `,
        context: { search_default_gb_foo: 1, search_default_gb_bar: 2 },
    });

    expect(queryFirst`.o_searchview_facet`).toHaveAttribute("aria-label", "Foo > Bar");
});

test("an expansion naming a field that vanished from the view is dropped", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `<search><field name="bar"/></search>`,
    });
    const { searchModel } = searchBar.env;
    const [item] = searchModel.getSearchItems((i) => i.type === "field");

    delete searchModel.searchViewFields.bar;
    await searchBar.computeState({ expanded: [item.id], query: "A" });

    expect(searchBar.state.expanded).toEqual([]);
});

test("property choices refresh through the field service and remain selectable", async () => {
    let selection = [["a", "Old"]];
    let reads = 0;
    onRpc("web_search_read", ({ kwargs }) => {
        if (kwargs.specification.child_properties) {
            reads++;
            return {
                records: [
                    {
                        id: 1,
                        display_name: "Parent",
                        child_properties: [
                            {
                                name: "p1",
                                string: "Status",
                                type: "selection",
                                selection,
                            },
                        ],
                    },
                ],
            };
        }
    });
    const bar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `<search><field name="properties"/></search>`,
    });
    await contains(".o_cp_searchview").click();
    await editSearch("Old");
    await contains(".o_expand").click();
    expect(".o_searchview_autocomplete").toHaveText(/Old/);
    selection = [
        ["a", "Renamed"],
        ["b", "Added"],
    ];
    await editSearch("Added");
    await contains(".o_expand").click();
    makeLogger("web.search.challenge").logic("property-choice-state", () => ({
        state: bar.state,
        subItems: bar.subItems,
        items: bar.items,
        open: bar.inputDropdownState.isOpen,
    }));
    expect(".o_searchview_autocomplete").toHaveText(/Status.*Added/);
    await contains(".o-dropdown-item:contains(Added)").click();
    makeLogger("web.search.challenge").logic("property-choice-selected", () => ({
        reads,
        domain: bar.env.searchModel.domain,
    }));
    expect(bar.env.searchModel.domain).toEqual([
        "&",
        ["bar", "=", 1],
        ["properties.p1", "=", "b"],
    ]);
    expect(reads).toBeGreaterThan(1);
});

test("replacing search text ignores a delayed close from the previous query", async () => {
    const bar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `<search><field name="foo"/></search>`,
    });
    await editSearch("Old");
    await editSearch("New");
    await animationFrame();
    makeLogger("web.search.challenge").logic("replacement-query", () => ({
        query: bar.state.query,
        input: bar.inputRef.el.value,
    }));
    expect(bar.state.query).toBe("New");
    expect(".o_searchview_input").toHaveValue("New");
    expect(".o_searchview_autocomplete").toHaveText(/New/);
});

test("same-named properties from two parents are both visible and select the chosen parent", async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        if (kwargs.specification.child_properties) {
            return {
                records: [1, 2].map((id) => ({
                    id,
                    display_name: `Parent ${id}`,
                    child_properties: [
                        {
                            name: "shared",
                            string: "Status",
                            type: "selection",
                            selection: [["a", "Available"]],
                        },
                    ],
                })),
            };
        }
    });
    const bar = await mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: [],
        searchViewId: false,
        searchViewArch: `<search><field name="properties"/></search>`,
    });
    await contains(".o_cp_searchview").click();
    await editSearch("Available");
    await contains(".o_expand").click();
    expect(".o_searchview_autocomplete").toHaveText(/Parent 1/);
    expect(".o_searchview_autocomplete").toHaveText(/Parent 2/);
    await contains(".o-dropdown-item:contains(Parent 2)").click();
    makeLogger("web.search.continue").logic("colliding-property-selected", () => ({
        domain: bar.env.searchModel.domain,
    }));
    expect(bar.env.searchModel.domain).toEqual([
        "&",
        ["bar", "=", 2],
        ["properties.shared", "=", "a"],
    ]);
});
