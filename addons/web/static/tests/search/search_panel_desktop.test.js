import { describe, expect, test } from "@odoo/hoot";
import { drag, queryAll, queryAllTexts, queryFirst, scroll } from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { Component, onWillUpdateProps, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineModels,
    defineParams,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { mountWithSearch } from "./helpers";

import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { WebClient } from "@web/webclient/webclient";

function parseContent(text) {
    const [value, counter] = text.split(/\s+/);
    return counter ? `${value}: ${counter}` : value;
}

function parseCounter(text) {
    const [, counter] = text.split(/\s+/);
    return isNaN(counter) ? null : Number(counter);
}

function getCategoriesContent() {
    return queryAllTexts`.o_search_panel_category_value header`.map(parseContent).filter(Boolean);
}

function getCategoriesCounter() {
    return queryAllTexts`.o_search_panel_category_value header`.map(parseCounter).filter(Boolean);
}

function getFiltersContent() {
    return queryAllTexts`.o_search_panel_filter_value`.map(parseContent).filter(Boolean);
}

function getFiltersCounter() {
    return queryAllTexts`.o_search_panel_filter_value`.map(parseCounter).filter(Boolean);
}

class TestComponent extends Component {
    static components = { SearchBarMenu, SearchPanel };
    static template = xml`
        <div class="o_test_component">
            <SearchPanel t-if="env.searchModel.display.searchPanel" />
            <SearchBarMenu />
        </div>
    `;
    static props = ["*"];

    setup() {
        this.domain = this.props.domain;
        onWillUpdateProps((np) => this.willUpdateProps(np));
    }

    async willUpdateProps(np) {
        this.domain = np.domain;
    }
}

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();
    bar = fields.Boolean();
    int_field = fields.Integer({ string: "Int Field", aggregator: "sum" });
    company_id = fields.Many2one({ string: "res.company", relation: "res.company" });
    company_ids = fields.Many2many({ string: "Companies", relation: "res.company" });
    category_id = fields.Many2one({ string: "category", relation: "category" });
    state = fields.Selection({
        selection: [
            ["abc", "ABC"],
            ["def", "DEF"],
            ["ghi", "GHI"],
        ],
    });

    _records = [
        {
            id: 1,
            bar: true,
            foo: "yop",
            int_field: 1,
            company_ids: [3],
            company_id: 3,
            state: "abc",
            category_id: 6,
        },
        {
            id: 2,
            bar: true,
            foo: "blip",
            int_field: 2,
            company_ids: [3],
            company_id: 5,
            state: "def",
            category_id: 7,
        },
        {
            id: 3,
            bar: true,
            foo: "gnap",
            int_field: 4,
            company_ids: [],
            company_id: 3,
            state: "ghi",
            category_id: 7,
        },
        {
            id: 4,
            bar: false,
            foo: "blip",
            int_field: 8,
            company_ids: [5],
            company_id: 5,
            state: "ghi",
            category_id: 7,
        },
    ];
    _views = {
        toy: /* xml */ `<toy/>`,
        list: /* xml */ `<tree><field name="foo"/></tree>`,
        kanban: /* xml */ `
            <kanban>
                <templates>
                    <div t-name="kanban-box" class="oe_kanban_global_click">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>
        `,
        form: /* xml */ `
            <form>
                <button name="1" type="action" string="multi view"/>
                <field name="foo"/>
                <field name="company_id"/>
            </form>
        `,
        pivot: /* xml */ `<pivot><field name="int_field" type="measure"/></pivot>`,
        search: /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                <filter name="filter" string="Filter" domain="[('bar', '=', true)]"/>
                <filter name="true_domain" string="True Domain" domain="[(1, '=', 1)]"/>
                <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                <searchpanel view_types="kanban,list,toy">
                    <field name="company_id" enable_counters="1" expand="1"/>
                    <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };
}

class Company extends models.Model {
    _name = "res.company";

    name = fields.Char();
    parent_id = fields.Many2one({ string: "Parent company", relation: "res.company" });
    category_id = fields.Many2one({ string: "Category", relation: "category" });

    _records = [
        { id: 3, name: "asustek", category_id: 6 },
        { id: 5, name: "agrolait", category_id: 7 },
    ];
}

class Category extends models.Model {
    name = fields.Char({ string: "Category Name" });

    _records = [
        { id: 6, name: "gold" },
        { id: 7, name: "silver" },
    ];
}

defineModels([Partner, Company, Category]);

defineActions([
    {
        id: 1,
        name: "Partners",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "kanban"],
            [false, "list"],
            [false, "pivot"],
            [false, "form"],
        ],
    },
    {
        id: 2,
        name: "Partners",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    },
]);

describe.current.tags("desktop");

test("basic rendering of a component without search panel", async () => {
    onRpc("*", (route) => {
        if (/search_panel_/.test(route)) {
            throw new Error("No search panel section should be loaded");
        }
    });
    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        display: { searchPanel: false },
    });
    expect(`.o_search_panel`).toHaveCount(0);
    expect(component.domain).toEqual([]); // initial domain
});

test("basic rendering of a component with empty search panel", async () => {
    Partner._views = {
        search: `<search><searchpanel/></search>`,
    };

    onRpc("*", (route, { model }) => {
        if (/search_panel_/.test(route)) {
            expect.step(`${route} on ${model}`);
        }
    });
    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel`).toHaveCount(0);
    expect(component.domain).toEqual([]); // initial domain
    expect([]).toVerifySteps();
});

test("basic rendering of a component with search panel", async () => {
    onRpc("*", (route, { method, model }) => {
        if (/search_panel_/.test(route)) {
            expect.step(`${method} on ${model}`);
        }
    });
    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel`).toHaveCount(1);
    expect(`.o_search_panel_section`).toHaveCount(2);

    const firstSection = `.o_search_panel_section:eq(0)`;
    expect(`${firstSection} .o_search_panel_section_header i`).toHaveClass("fa-folder");
    expect(`${firstSection} .o_search_panel_section_header`).toHaveText(/company/i);
    expect(`${firstSection} .o_search_panel_category_value`).toHaveCount(3);
    expect(`${firstSection} .o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(queryAllTexts`${firstSection} .o_search_panel_category_value`).toEqual([
        "All",
        "asustek\n2",
        "agrolait\n2",
    ]);

    const secondSection = `.o_search_panel_section:eq(1)`;
    expect(`${secondSection} .o_search_panel_section_header i`).toHaveClass("fa-filter");
    expect(`${secondSection} .o_search_panel_section_header`).toHaveText(/category/i);
    expect(`${secondSection} .o_search_panel_filter_value`).toHaveCount(2);
    expect(queryAllTexts`${secondSection} .o_search_panel_filter_value`).toEqual([
        "gold\n1",
        "silver\n3",
    ]);

    expect([
        "search_panel_select_range on partner",
        "search_panel_select_multi_range on partner",
    ]).toVerifySteps();
    expect(component.domain).toEqual([]); // initial domain (does not need the sections to be loaded)
});

test("sections with custom icon and color", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel view_types="toy">
                    <field name="company_id" icon="fa-car" color="blue" enable_counters="1"/>
                    <field name="state" select="multi" icon="fa-star" color="#000" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };
    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });

    expect(`.o_search_panel_section_header:eq(0) i`).toHaveClass("fa-car");
    expect(`.o_search_panel_section_header:eq(0) i`).toHaveStyle({ color: "rgb(0, 0, 255)" });
    expect(`.o_search_panel_section_header:eq(1) i`).toHaveClass("fa-star");
    expect(`.o_search_panel_section_header:eq(1) i`).toHaveStyle({ color: "rgb(0, 0, 0)" });
    expect(component.domain).toEqual([]);
});

test(`sections with attr invisible="1" are ignored`, async () => {
    // 'groups' attributes are converted server-side into invisible="1" when the user doesn't
    // belong to the given group
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                    <field name="state" select="multi" invisible="1" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("*", (route, { method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(`${method}`);
        }
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_section`).toHaveCount(1);
    expect(["search_panel_select_range"]).toVerifySteps();
});

test("categories and filters order is kept", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                    <field name="category_id" select="multi" enable_counters="1"/>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_section`).toHaveCount(3);
    expect(queryAllTexts`.o_search_panel_section_header`).toEqual([
        "RES.COMPANY",
        "CATEGORY",
        "STATE",
    ]);
});

test("specify active category value in context and manually change category", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        context: {
            searchpanel_default_company_id: false,
            searchpanel_default_state: "ghi",
        },
    });
    expect(
        queryAllTexts`.o_search_panel_category_value header.active .o_search_panel_label`
    ).toEqual(["All", "GHI"]);
    expect(component.domain).toEqual([["state", "=", "ghi"]]);

    // select 'ABC' in the category 'state'
    await contains(queryAll`.o_search_panel_category_value header`[4]).click();
    expect(
        queryAllTexts`.o_search_panel_category_value header.active .o_search_panel_label`
    ).toEqual(["All", "ABC"]);
    expect(component.domain).toEqual([["state", "=", "abc"]]);
});

test("use category (on many2one) to refine search", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        domain: [["bar", "=", true]],
        context: {
            searchpanel_default_company_id: false,
            searchpanel_default_state: "ghi",
        },
    });
    expect(component.domain).toEqual([["bar", "=", true]]);

    // select "asustek"
    await contains(queryAll`.o_search_panel_category_value header`[1]).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(1) .active`).toHaveCount(1);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "child_of", 3]]);

    // select "agrolait"
    await contains(queryAll`.o_search_panel_category_value header`[2]).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(2) .active`).toHaveCount(1);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "child_of", 5]]);

    // select "All"
    await contains(queryAll`.o_search_panel_category_value header`[0]).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(component.domain).toEqual([["bar", "=", true]]);
});

test("use category (on selection) to refine search", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(component.domain).toEqual([]);

    // select 'abc'
    await contains(`.o_search_panel_category_value:nth-of-type(2) header`).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:nth-of-type(2) .active`).toHaveCount(1);
    expect(component.domain).toEqual([["state", "=", "abc"]]);

    // select 'ghi'
    await contains(`.o_search_panel_category_value:nth-of-type(4) header`).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:nth-of-type(4) .active`).toHaveCount(1);
    expect(component.domain).toEqual([["state", "=", "ghi"]]);

    // select 'All' again
    await contains(`.o_search_panel_category_value:nth-of-type(1) header`).click();
    expect(`.o_search_panel_category_value:nth-of-type(1) .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(component.domain).toEqual([]);
});

test("category has been archived", async () => {
    Company._fields.active = fields.Boolean({ string: "Archived" });
    Company._records = [
        { id: 3, name: "asustek" },
        {
            name: "Company 5",
            id: 5,
            active: true,
        },
        {
            name: "child of 5 archived",
            parent_id: 5,
            id: 666,
            active: false,
        },
        {
            name: "child of 666",
            parent_id: 666,
            id: 777,
            active: true,
        },
    ];
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_category_value`).toHaveCount(2);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
});

test("use two categories to refine search", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        domain: [["bar", "=", true]],
    });
    expect(component.domain).toEqual([["bar", "=", true]]);
    expect(`.o_search_panel_section`).toHaveCount(2);

    // select 'asustek'
    await contains(
        `.o_search_panel_category_value header .o_search_panel_label_title:contains(asustek)`
    ).click();
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "child_of", 3]]);

    // select 'abc'
    await contains(
        `.o_search_panel_category_value header .o_search_panel_label_title:contains(abc)`
    ).click();
    expect(component.domain).toEqual([
        "&",
        ["bar", "=", true],
        "&",
        ["company_id", "child_of", 3],
        ["state", "=", "abc"],
    ]);

    // select 'ghi'
    await contains(
        `.o_search_panel_category_value header .o_search_panel_label_title:contains(ghi)`
    ).click();
    expect(component.domain).toEqual([
        "&",
        ["bar", "=", true],
        "&",
        ["company_id", "child_of", 3],
        ["state", "=", "ghi"],
    ]);

    // select 'All' in first category (company_id)
    await contains(`.o_search_panel_section:eq(0) .o_search_panel_category_value header`).click();
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["state", "=", "ghi"]]);

    // select 'All' in second category (state)
    await contains(`.o_search_panel_section:eq(1) .o_search_panel_category_value header`).click();
    expect(component.domain).toEqual([["bar", "=", true]]);
});

test("category with parent_field", async () => {
    Company._records.push(
        { id: 40, name: "child company 1", parent_id: 5 },
        { id: 41, name: "child company 2", parent_id: 5 }
    );
    Partner._records[1].company_id = 40;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });

    // 'All' is selected by default
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value`).toHaveCount(3);
    expect(`.o_search_panel_category_value .o_toggle_fold > i`).toHaveCount(1);

    // unfold parent category and select 'All' again
    await contains(`.o_search_panel_category_value header:eq(2)`).click();
    await contains(`.o_search_panel_category_value header:eq(0)`).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value`).toHaveCount(5);
    expect(`.o_search_panel_category_value .o_search_panel_category_value`).toHaveCount(2);
    expect(component.domain).toEqual([]);

    // click on first child company
    await contains(`.o_search_panel_category_value header:eq(3)`).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(
        `.o_search_panel_category_value .o_search_panel_category_value:first .active`
    ).toHaveCount(1);
    expect(component.domain).toEqual([["company_id", "child_of", 40]]);

    // click on parent company
    await contains(`.o_search_panel_category_value header:eq(2)`).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(2) .active`).toHaveCount(1);
    expect(component.domain).toEqual([["company_id", "child_of", 5]]);

    // fold parent company by clicking on it
    await contains(`.o_search_panel_category_value header:eq(2)`).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(2) .active`).toHaveCount(1);

    // parent company should be folded
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(2) .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value`).toHaveCount(3);
    expect(component.domain).toEqual([["company_id", "child_of", 5]]);

    // fold category with children
    await contains(`.o_search_panel_category_value header:eq(2)`).click();
    await contains(`.o_search_panel_category_value header:eq(2)`).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(2) .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value`).toHaveCount(3);
    expect(component.domain).toEqual([["company_id", "child_of", 5]]);
});

test("category with no parent_field", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(component.domain).toEqual([]);

    // 'All' is selected by default
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value`).toHaveCount(3);

    // click on 'gold' category
    await contains(queryAll`.o_search_panel_category_value header`[1]).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(1) .active`).toHaveCount(1);
    expect(component.domain).toEqual([["category_id", "=", 6]]); // must use '=' operator (instead of 'child_of')
});

test("can (un)fold parent category values", async () => {
    Company._records.push(
        { id: 40, name: "child company 1", parent_id: 5 },
        { id: 41, name: "child company 2", parent_id: 5 }
    );
    Partner._records[1].company_id = 40;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i`).toHaveCount(1);
    expect(
        `.o_search_panel_category_value header:contains(agrolait) .o_toggle_fold > i`
    ).toHaveClass("fa-caret-right");
    expect(`.o_search_panel_category_value`).toHaveCount(3);

    // unfold agrolait
    await contains(
        `.o_search_panel_category_value header:contains(agrolait) .o_toggle_fold > i`
    ).click();
    expect(
        `.o_search_panel_category_value header:contains(agrolait) .o_toggle_fold > i`
    ).toHaveClass("fa-caret-down");
    expect(`.o_search_panel_category_value`).toHaveCount(5);

    // fold agrolait
    await contains(
        `.o_search_panel_category_value header:contains(agrolait) .o_toggle_fold > i`
    ).click();
    expect(
        `.o_search_panel_category_value header:contains(agrolait) .o_toggle_fold > i`
    ).toHaveClass("fa-caret-right");
    expect(`.o_search_panel_category_value`).toHaveCount(3);
});

test("fold status is kept at reload", async () => {
    Company._records.push(
        { id: 40, name: "child company 1", parent_id: 5 },
        { id: 41, name: "child company 2", parent_id: 5 }
    );
    Partner._records[1].company_id = 40;
    Partner._views = {
        search: /* xml */ `
            <search>
                <filter name="True Domain" domain="[(1, '=', 1)]"/>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });

    // unfold agrolait
    await contains(queryFirst`.o_search_panel_category_value > header:contains(agrolait)`).click();
    expect(
        queryFirst`.o_search_panel_category_value > header:contains(agrolait) .o_toggle_fold > i`
    ).toHaveClass("fa-caret-down");
    expect(`.o_search_panel_category_value`).toHaveCount(5);

    await toggleSearchBarMenu();
    await toggleMenuItem("True Domain");
    expect(
        queryFirst`.o_search_panel_category_value > header:contains(agrolait) .o_toggle_fold > i`
    ).toHaveClass("fa-caret-down");
    expect(`.o_search_panel_category_value`).toHaveCount(5);
});

test("concurrency: delayed component update", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    let promise = new Deferred();
    class DeferredTestComponent extends TestComponent {
        async willUpdateProps(np) {
            await promise;
            super.willUpdateProps(np);
        }
    }
    const component = await mountWithSearch(DeferredTestComponent, {
        resModel: "partner",
        searchViewId: false,
        domain: [["bar", "=", true]],
    });

    // 'All' should be selected by default
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(component.domain).toEqual([["bar", "=", true]]);

    // select 'asustek' (delay the reload)
    const asustekPromise = promise;
    await contains(`.o_search_panel_category_value:eq(1) header`).click();

    // 'asustek' should not be selected yet, and there should still be 3 records
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(component.domain).toEqual([["bar", "=", true]]);

    // select 'agrolait' (delay the reload)
    promise = new Deferred();
    const agrolaitPromise = promise;
    await contains(`.o_search_panel_category_value:eq(2) header`).click();

    // 'agrolait' should not be selected yet, and there should still be 3 records
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(component.domain).toEqual([["bar", "=", true]]);

    // unlock asustek search (should be ignored, so there should still be 3 records)
    asustekPromise.resolve();
    await animationFrame();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "child_of", 3]]);

    // unlock agrolait search, there should now be 1 record
    agrolaitPromise.resolve();
    await animationFrame();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(2) .active`).toHaveCount(1);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "child_of", 5]]);
});

test("concurrency: single category", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '=', 1)]"/>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    let promise = new Deferred();
    onRpc("*", async (route, { method }) => {
        await promise;
        expect.step(method || route);
    });
    const compPromise = mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        context: {
            searchpanel_default_company_id: [5],
        },
    });

    // Case 1: search panel is awaited to build the query with search defaults
    await animationFrame();
    expect([]).toVerifySteps();

    promise.resolve();
    await compPromise;
    expect(["get_views", "search_panel_select_range"]).toVerifySteps();

    // Case 2: search domain changed so we wait for the search panel once again
    promise = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("Filter");
    expect([]).toVerifySteps();

    promise.resolve();
    await animationFrame();
    expect(["search_panel_select_range"]).toVerifySteps();

    // Case 3: search domain is the same and default values do not matter anymore
    promise = new Deferred();
    await contains(`.o_search_panel_category_value header:eq(1)`).click();

    // The search read is executed right away in this case
    expect([]).toVerifySteps();
    promise.resolve();
    await animationFrame();
    expect(["search_panel_select_range"]).toVerifySteps();
});

test("concurrency: category and filter", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id" enable_counters="1"/>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const promise = new Deferred();
    onRpc("*", async (route, { method }) => {
        await promise;
        expect.step(method || route);
    });
    const compPromise = mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        context: {
            searchpanel_default_company_id: [5],
        },
    });

    await animationFrame();
    expect([]).toVerifySteps();

    promise.resolve();
    await compPromise;
    expect([
        "get_views",
        "search_panel_select_range",
        "search_panel_select_multi_range",
    ]).toVerifySteps();
});

test("concurrency: category and filter with a domain", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id"/>
                    <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const promise = new Deferred();
    onRpc("*", async (route, { method }) => {
        await promise;
        expect.step(method || route);
    });
    const compPromise = mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });

    await animationFrame();
    expect([]).toVerifySteps();

    promise.resolve();
    await compPromise;
    expect([
        "get_views",
        "search_panel_select_range",
        "search_panel_select_multi_range",
    ]).toVerifySteps();
});

test("concurrency: misordered get_filters", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" enable_counters="1"/>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    let promise;
    onRpc("search_panel_select_multi_range", () => promise);
    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });

    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(component.domain).toEqual([]);

    // select 'abc' (delay the reload)
    promise = new Deferred();
    const abcDef = promise;
    await contains(`.o_search_panel_category_value header:eq(1)`).click();

    // 'All' should still be selected
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(component.domain).toEqual([["state", "=", "abc"]]);

    // select 'ghi' (delay the reload)
    promise = new Deferred();
    const ghiDef = promise;
    await contains(`.o_search_panel_category_value header:eq(3)`).click();

    // 'All' should still be selected
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(component.domain).toEqual([["state", "=", "ghi"]]);

    // unlock ghi search
    ghiDef.resolve();
    await animationFrame();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(3) .active`).toHaveCount(1);
    expect(component.domain).toEqual([["state", "=", "ghi"]]);

    // unlock abc search (should be ignored)
    abcDef.resolve();
    await animationFrame();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(3) .active`).toHaveCount(1);
    expect(component.domain).toEqual([["state", "=", "ghi"]]);
});

test("concurrency: delayed get_filter", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '=', 1)]"/>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    let promise;
    onRpc("search_panel_select_multi_range", () => promise);
    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(component.domain).toEqual([]);

    // trigger a reload and delay the get_filter
    promise = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("Filter");
    expect(component.domain).toEqual([]);

    promise.resolve();
    await animationFrame();
    expect(component.domain).toEqual([["id", "=", 1]]);
});

test("use filter (on many2one) to refine search", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '=', 1)]"/>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        domain: [["bar", "=", true]],
    });
    expect(`.o_search_panel_filter_value`).toHaveCount(2);
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(0);
    expect(getFiltersContent()).toEqual(["asustek: 2", "agrolait: 1"]);
    expect(component.domain).toEqual([["bar", "=", true]]);

    // check 'asustek'
    await contains(queryAll`.o_search_panel_filter_value:eq(0) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(getFiltersContent()).toEqual(["asustek: 2", "agrolait: 1"]);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "in", [3]]]);

    // check 'agrolait'
    await contains(queryAll`.o_search_panel_filter_value:eq(1) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(2);
    expect(getFiltersContent()).toEqual(["asustek: 2", "agrolait: 1"]);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "in", [3, 5]]]);

    // uncheck 'asustek'
    await contains(queryAll`.o_search_panel_filter_value:eq(0) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(getFiltersContent()).toEqual(["asustek: 2", "agrolait: 1"]);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "in", [5]]]);

    // uncheck 'agrolait'
    await contains(queryAll`.o_search_panel_filter_value:eq(1) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(0);
    expect(getFiltersContent()).toEqual(["asustek: 2", "agrolait: 1"]);
    expect(component.domain).toEqual([["bar", "=", true]]);
});

test("use filter (on selection) to refine search", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '=', 1)]"/>
                <searchpanel>
                    <field name="state" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        domain: [["bar", "=", true]],
    });
    expect(`.o_search_panel_filter_value`).toHaveCount(3);
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(0);
    expect(getFiltersContent()).toEqual(["ABC: 1", "DEF: 1", "GHI: 1"]);
    expect(component.domain).toEqual([["bar", "=", true]]);

    // check 'abc'
    await contains(queryAll`.o_search_panel_filter_value:eq(0) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(getFiltersContent()).toEqual(["ABC: 1", "DEF: 1", "GHI: 1"]);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["state", "in", ["abc"]]]);

    // check 'def'
    await contains(queryAll`.o_search_panel_filter_value:eq(1) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(2);
    expect(getFiltersContent()).toEqual(["ABC: 1", "DEF: 1", "GHI: 1"]);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["state", "in", ["abc", "def"]]]);

    // uncheck 'abc'
    await contains(queryAll`.o_search_panel_filter_value:eq(0) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(getFiltersContent()).toEqual(["ABC: 1", "DEF: 1", "GHI: 1"]);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["state", "in", ["def"]]]);

    // uncheck 'def'
    await contains(queryAll`.o_search_panel_filter_value:eq(1) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(0);
    expect(getFiltersContent()).toEqual(["ABC: 1", "DEF: 1", "GHI: 1"]);
    expect(component.domain).toEqual([["bar", "=", true]]);
});

test("only reload categories and filters when domains change (counters disabled, selection)", async () => {
    Partner._views = {
        search: /* xml */ `
                <search>
                    <filter name="Filter" domain="[('id', '&lt;', 5)]"/>
                    <searchpanel>
                        <field name="state" expand="1"/>
                        <field name="company_id" select="multi" enable_counters="1" expand="1"/>
                    </searchpanel>
                </search>
            `,
    };

    onRpc("*", (route, { method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(method);
        }
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });

    expect(["search_panel_select_range", "search_panel_select_multi_range"]).toVerifySteps();

    // reload with another domain, so the filters should be reloaded
    await toggleSearchBarMenu();
    await toggleMenuItem("Filter");
    expect(["search_panel_select_multi_range"]).toVerifySteps();

    // change category value, so the filters should be reloaded
    await contains(`.o_search_panel_category_value header:eq(1)`).click();
    expect(["search_panel_select_multi_range"]).toVerifySteps();
});

test("only reload categories and filters when domains change (counters disabled, many2one)", async () => {
    Partner._views = {
        search: /* xml */ `
                <search>
                    <filter name="domain" domain="[('id', '&lt;', 5)]"/>
                    <searchpanel>
                        <field name="category_id" expand="1"/>
                        <field name="company_id" select="multi" enable_counters="1" expand="1"/>
                    </searchpanel>
                </search>
            `,
    };

    onRpc("*", (route, { method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(method);
        }
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(["search_panel_select_range", "search_panel_select_multi_range"]).toVerifySteps();

    // reload with another domain, so the filters should be reloaded
    await toggleSearchBarMenu();
    await toggleMenuItem("domain");
    expect(["search_panel_select_multi_range"]).toVerifySteps();

    // change category value, so the filters should be reloaded
    await contains(`.o_search_panel_category_value header:eq(1)`).click();
    expect(["search_panel_select_multi_range"]).toVerifySteps();
});

test("category counters", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '&lt;', 3)]"/>
                <searchpanel>
                    <field name="state" enable_counters="1" expand="1"/>
                    <field name="company_id" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("*", (route, { args, method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(method);
        }
        if (method === "search_panel_select_range") {
            expect.step(args[0]);
        }
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect([
        "search_panel_select_range",
        "state",
        "search_panel_select_range",
        "company_id",
    ]).toVerifySteps();
    expect(getCategoriesContent()).toEqual([
        "All",
        "ABC: 1",
        "DEF: 1",
        "GHI: 2",
        "All",
        "asustek",
        "agrolait",
    ]);

    // reload with another domain, so the categories 'state' and 'company_id' should be reloaded
    await toggleSearchBarMenu();
    await toggleMenuItem("Filter");
    expect(["search_panel_select_range", "state"]).toVerifySteps();
    expect(getCategoriesContent()).toEqual([
        "All",
        "ABC: 1",
        "DEF: 1",
        "GHI",
        "All",
        "asustek",
        "agrolait",
    ]);

    // change category value, so the category 'state' should be reloaded
    await contains(`.o_search_panel_category_value header:eq(1)`).click();
    expect(["search_panel_select_range", "state"]).toVerifySteps();
    expect(getCategoriesContent()).toEqual([
        "All",
        "ABC: 1",
        "DEF: 1",
        "GHI",
        "All",
        "asustek",
        "agrolait",
    ]);
});

test("category selection without counters", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '&lt;', 3)]"/>
                <searchpanel>
                    <field name="state" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("*", (route, { args, method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(method);
        }
        if (method === "search_panel_select_range") {
            expect.step(args[0]);
        }
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(["search_panel_select_range", "state"]).toVerifySteps();
    expect(getCategoriesContent()).toEqual(["All", "ABC", "DEF", "GHI"]);

    // reload with another domain, so the category 'state' should be reloaded
    await toggleSearchBarMenu();
    await toggleMenuItem("Filter");
    expect([]).toVerifySteps();
    expect(getCategoriesContent()).toEqual(["All", "ABC", "DEF", "GHI"]);

    // change category value, so the category 'state' should be reloaded
    await contains(`.o_search_panel_category_value header:eq(1)`).click();
    expect([]).toVerifySteps();
    expect(getCategoriesContent()).toEqual(["All", "ABC", "DEF", "GHI"]);
});

test("filter with groupby", async () => {
    Company._records.push({ id: 11, name: "camptocamp", category_id: 7 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        domain: [["bar", "=", true]],
    });
    expect(`.o_search_panel_filter_group`).toHaveCount(2);
    expect(`.o_search_panel_filter_group:first .o_search_panel_filter_value`).toHaveCount(1);
    expect(`.o_search_panel_filter_group:eq(0) header`).toHaveText("gold");
    expect(queryAllTexts`.o_search_panel_filter_group:eq(0) .o_search_panel_filter_value`).toEqual([
        "asustek\n2",
    ]);
    expect(`.o_search_panel_filter_group:eq(1) .o_search_panel_filter_value`).toHaveCount(2);
    expect(`.o_search_panel_filter_group:eq(1) header`).toHaveText("silver");
    expect(queryAllTexts`.o_search_panel_filter_group:eq(1) .o_search_panel_filter_value`).toEqual([
        "agrolait\n1",
        "camptocamp",
    ]);
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(0);
    expect(component.domain).toEqual([["bar", "=", true]]);

    // check 'asustek'
    await contains(queryAll`.o_search_panel_filter_value:eq(0) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(queryFirst(`.o_search_panel_filter_group:eq(0) header > div > input`)).toBeChecked();
    expect(getFiltersContent()).toEqual(["asustek: 2", "agrolait", "camptocamp"]);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "in", [3]]]);

    // check 'agrolait'
    await contains(queryAll`.o_search_panel_filter_value:eq(1) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(2);
    expect(queryFirst(`.o_search_panel_filter_group:eq(1) header > div > input`)).not.toBeChecked();
    expect(queryFirst(`.o_search_panel_filter_group:eq(1) header > div > input`)).toBeChecked({
        indeterminate: true,
    });
    expect(getFiltersContent()).toEqual(["asustek", "agrolait", "camptocamp"]);
    expect(component.domain).toEqual([
        "&",
        ["bar", "=", true],
        "&",
        ["company_id", "in", [3]],
        ["company_id", "in", [5]],
    ]);

    // check 'camptocamp'
    await contains(queryAll`.o_search_panel_filter_value:eq(2) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(3);
    expect(queryAll`.o_search_panel_filter_value:eq(1) input`).toBeChecked();
    expect(queryAll`.o_search_panel_filter_value:eq(1) input`).not.toBeChecked({
        indeterminate: true,
    });
    expect(getFiltersContent()).toEqual(["asustek", "agrolait", "camptocamp"]);
    expect(component.domain).toEqual([
        "&",
        ["bar", "=", true],
        "&",
        ["company_id", "in", [3]],
        ["company_id", "in", [5, 11]],
    ]);

    // uncheck second group
    await contains(`.o_search_panel_filter_group:eq(1) header > div > input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(queryAll`.o_search_panel_filter_value:eq(1) input`).not.toBeChecked();
    expect(queryAll`.o_search_panel_filter_value:eq(1) input`).not.toBeChecked({
        indeterminate: true,
    });
    expect(getFiltersContent()).toEqual(["asustek: 2", "agrolait", "camptocamp"]);
    expect(component.domain).toEqual(["&", ["bar", "=", true], ["company_id", "in", [3]]]);
});

test("filter with domain", async () => {
    Company._records.push({ id: 40, name: "child company 1", parent_id: 3 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" domain="[('parent_id','=',False)]" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("search_panel_select_multi_range", (_, { kwargs }) => {
        expect.step("search_panel_select_multi_range");
        expect({ ...kwargs, context: {} }).toEqual({
            group_by: false,
            category_domain: [],
            context: {},
            expand: true,
            filter_domain: [],
            search_domain: [],
            comodel_domain: [["parent_id", "=", false]],
            group_domain: [],
            enable_counters: true,
            limit: 200,
        });
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_filter_value`).toHaveCount(2);
    expect(getFiltersContent()).toEqual(["asustek: 2", "agrolait: 2"]);
    expect(["search_panel_select_multi_range"]).toVerifySteps();
});

test("filter with domain depending on category", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id"/>
                    <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("search_panel_select_multi_range", (_, { kwargs }) => {
        // the following keys should have same value for all calls to this route
        const { group_by, search_domain, filter_domain } = kwargs;
        expect({ group_by, search_domain, filter_domain }).toEqual({
            group_by: false,
            filter_domain: [],
            search_domain: [],
        });
        expect.step(JSON.stringify(kwargs.category_domain));
        expect.step(JSON.stringify(kwargs.comodel_domain));
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });

    // select 'gold' category
    await contains(`.o_search_panel_category_value:eq(1) header`).click();
    expect(`.o_search_panel_category_value .active`).toHaveCount(1);
    expect(`.o_search_panel_category_value:eq(1) .active`).toHaveCount(1);
    expect(`.o_search_panel_filter_value`).toHaveCount(1);
    expect(getFiltersContent()).toEqual(["asustek: 1"]);

    // select 'silver' category
    await contains(`.o_search_panel_category_value:eq(2) header`).click();
    expect(`.o_search_panel_category_value:eq(2) .active`).toHaveCount(1);
    expect(`.o_search_panel_filter_value`).toHaveCount(1);
    expect(getFiltersContent()).toEqual(["agrolait: 2"]);

    // select All
    await contains(`.o_search_panel_category_value:eq(0) header`).click();
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
    expect(`.o_search_panel_filter_value`).toHaveCount(0);
    expect([
        "[]", // category_domain (All)
        '[["category_id","=",false]]', // comodel_domain (All)
        '[["category_id","=",6]]', // category_domain ('gold')
        '[["category_id","=",6]]', // comodel_domain ('gold')
        '[["category_id","=",7]]', // category_domain ('silver')
        '[["category_id","=",7]]', // comodel_domain ('silver')
        "[]", // category_domain (All)
        '[["category_id","=",false]]', // comodel_domain (All)
    ]).toVerifySteps();
});

test("specify active filter values in context", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                    <field name="state" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        context: {
            searchpanel_default_company_id: [5],
            searchpanel_default_state: ["abc", "ghi"],
        },
    });
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(3);
    expect(component.domain).toEqual([
        "&",
        ["company_id", "in", [5]],
        ["state", "in", ["abc", "ghi"]],
    ]);

    // manually untick a default value
    await contains(queryAll`.o_search_panel_filter_value:eq(1) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(2);
    expect(component.domain).toEqual([["state", "in", ["abc", "ghi"]]]);
});

test("retrieved filter value from context does not exist", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        context: {
            searchpanel_default_company_id: [1, 3],
        },
    });
    expect(component.domain).toEqual([["company_id", "in", [3]]]);
});

test("filter with groupby and default values in context", async () => {
    Company._records.push({ id: 11, name: "camptocamp", category_id: 7 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    const component = await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        context: {
            searchpanel_default_company_id: [5],
        },
    });
    expect(queryFirst`.o_search_panel_filter_group:eq(1) header > div > input`).toBeChecked({
        indeterminate: true,
    });
    expect(component.domain).toEqual([["company_id", "in", [5]]]);
});

test('Does not confuse false and "false" groupby values', async () => {
    Company._fields.char_field = fields.Char({ string: "Char Field" });
    Company._records = [
        { id: 3, name: "A", char_field: false },
        { id: 5, name: "B", char_field: "false" },
    ];
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="char_field"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        context: {
            searchpanel_default_company_id: [5],
        },
    });
    expect(`.o_search_panel_section`).toHaveCount(1);

    // There should be a group 'false' displayed with only value B inside it.
    expect(`.o_search_panel_filter_group`).toHaveCount(1);
    expect(`.o_search_panel_filter_group header`).toHaveText("false");
    expect(queryAllTexts`.o_search_panel_filter_group:eq(0) .o_search_panel_filter_value`).toEqual([
        "B",
    ]);
    expect(`.o_search_panel_filter_group .o_search_panel_filter_value`).toHaveCount(1);

    // Globally, there should be two values, one displayed in the group 'false', and one at the end of the section
    // (the group false is not displayed and its values are displayed at the first level)
    expect(`.o_search_panel_filter_value`).toHaveCount(2);
    expect(getFiltersContent()).toEqual(["B", "A"]);
});

test("tests conservation of category record order", async () => {
    Company._records.push(
        { id: 56, name: "highID", category_id: 6 },
        { id: 2, name: "lowID", category_id: 6 }
    );
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                    <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(getCategoriesContent()).toEqual(["All", "lowID", "asustek: 2", "agrolait: 2", "highID"]);
});

test("search panel is available on list and kanban by default", async () => {
    Partner._views = {
        ...Partner._views,
        [["search", false]]: /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                <filter name="filter" string="Filter" domain="[('bar', '=', true)]"/>
                <filter name="true_domain" string="True Domain" domain="[(1, '=', 1)]"/>
                <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                    <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_kanban_view .o_content.o_component_with_search_panel`).toHaveCount(1);
    expect(`.o_content.o_component_with_search_panel .o_search_panel`).toHaveCount(1);

    await getService("action").switchView("pivot");
    expect(`.o_pivot_view .o_content`).toHaveCount(1);
    expect(`.o_pivot_view .o_content .o_search_panel`).toHaveCount(0);

    await getService("action").switchView("list");
    expect(`.o_list_view .o_content.o_component_with_search_panel`).toHaveCount(1);
    expect(`.o_content.o_component_with_search_panel .o_search_panel`).toHaveCount(1);

    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_form_view .o_content`).toHaveCount(1);
    expect(`.o_form_view .o_content .o_search_panel`).toHaveCount(0);
});

test("search panel with view_types attribute", async () => {
    Partner._views = {
        ...Partner._views,
        [["search", false]]: /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                <filter name="filter" string="Filter" domain="[('bar', '=', true)]"/>
                <filter name="true_domain" string="True Domain" domain="[(1, '=', 1)]"/>
                <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                <searchpanel view_types="kanban,pivot">
                    <field name="company_id" enable_counters="1" expand="1"/>
                    <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_kanban_view .o_content.o_component_with_search_panel`).toHaveCount(1);
    expect(`.o_content.o_component_with_search_panel .o_search_panel`).toHaveCount(1);

    await getService("action").switchView("list");
    expect(`.o_list_view .o_content`).toHaveCount(1);
    expect(`.o_content .o_search_panel`).toHaveCount(0);

    await getService("action").switchView("pivot");
    expect(`.o_content.o_component_with_search_panel .o_pivot`).toHaveCount(1);
    expect(`.o_content.o_component_with_search_panel .o_search_panel`).toHaveCount(1);
});

test("search panel state is shared between views", async () => {
    onRpc("web_search_read", (_, { kwargs }) => {
        expect.step(JSON.stringify(kwargs.domain));
    });
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_search_panel_category_value header:eq(0)`).toHaveClass("active");
    expect(`.o_kanban_record:not(.o_kanban_ghost)`).toHaveCount(4);

    // select 'asustek' company
    await contains(`.o_search_panel_category_value header:eq(1)`).click();
    expect(`.o_search_panel_category_value header:eq(1)`).toHaveClass("active");
    expect(`.o_kanban_record:not(.o_kanban_ghost)`).toHaveCount(2);

    await getService("action").switchView("list");
    expect(`.o_search_panel_category_value header:eq(1)`).toHaveClass("active");
    expect(`.o_data_row`).toHaveCount(2);

    // select 'agrolait' company
    await contains(`.o_search_panel_category_value header:eq(2)`).click();
    expect(`.o_search_panel_category_value header:eq(2)`).toHaveClass("active");
    expect(`.o_data_row`).toHaveCount(2);

    await getService("action").switchView("kanban");
    expect(`.o_search_panel_category_value header:eq(2)`).toHaveClass("active");
    expect(`.o_kanban_record:not(.o_kanban_ghost)`).toHaveCount(2);
    expect([
        "[]", // initial search_read
        '[["company_id","child_of",3]]', // kanban, after selecting the first company
        '[["company_id","child_of",3]]', // list
        '[["company_id","child_of",5]]', // list, after selecting the other company
        '[["company_id","child_of",5]]', // kanban
    ]).toVerifySteps();
});

test("search panel filters are kept between switch views", async () => {
    onRpc("web_search_read", (_, { kwargs }) => {
        expect.step(JSON.stringify(kwargs.domain));
    });
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(0);
    expect(`.o_kanban_record:not(.o_kanban_ghost)`).toHaveCount(4);

    // select gold filter
    await contains(queryAll`.o_search_panel_filter_value:eq(0) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(`.o_kanban_record:not(.o_kanban_ghost)`).toHaveCount(1);

    await getService("action").switchView("list");
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(1);

    // select silver filter
    await contains(queryAll`.o_search_panel_filter_value:eq(1) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(2);
    expect(`.o_data_row`).toHaveCount(4);

    await getService("action").switchView("kanban");
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(2);
    expect(`.o_kanban_record:not(.o_kanban_ghost)`).toHaveCount(4);

    await contains(`.o_kanban_record`).click();
    await contains(`.breadcrumb-item`).click();
    expect([
        "[]", // initial search_read
        '[["category_id","in",[6]]]', // kanban, after selecting the gold filter
        '[["category_id","in",[6]]]', // list
        '[["category_id","in",[6,7]]]', // list, after selecting the silver filter
        '[["category_id","in",[6,7]]]', // kanban
        '[["category_id","in",[6,7]]]', // kanban, after switching back from form view
    ]).toVerifySteps();
});

test("search panel filters are kept when switching to a view with no search panel", async () => {
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_kanban_view .o_content.o_component_with_search_panel`).toHaveCount(1);
    expect(`.o_content.o_component_with_search_panel .o_search_panel`).toHaveCount(1);
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(0);
    expect(`.o_kanban_record:not(.o_kanban_ghost)`).toHaveCount(4);

    // select gold filter
    await contains(queryAll`.o_search_panel_filter_value:eq(0) input`).click();
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(`.o_kanban_record:not(.o_kanban_ghost)`).toHaveCount(1);

    // switch to pivot
    await getService("action").switchView("pivot");
    expect(`.o_pivot_view .o_content`).toHaveCount(1);
    expect(`.o_content .o_search_panel`).toHaveCount(0);
    expect(`.o_pivot_cell_value`).toHaveText("15");

    // switch to list
    await getService("action").switchView("list");
    expect(`.o_list_view .o_content.o_component_with_search_panel`).toHaveCount(1);
    expect(`.o_content.o_component_with_search_panel .o_search_panel`).toHaveCount(1);
    expect(`.o_search_panel_filter_value input:checked`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(1);
});

test('after onExecuteAction, selects "All" as default category value', async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1, { viewType: "form" });
    await contains(`.o_form_view .o_form_nosheet button`).click();
    expect(`.o_kanban_view`).toHaveCount(1);
    expect(`.o_search_panel`).toHaveCount(1);
    expect(`.o_search_panel_category_value:first .active`).toHaveCount(1);
});

test("categories and filters are not reloaded when switching between views", async () => {
    onRpc("*", (route, { method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(method);
        }
    });
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await getService("action").switchView("list");
    await getService("action").switchView("kanban");
    expect([
        "search_panel_select_range", // kanban: categories
        "search_panel_select_multi_range", // kanban: filters
    ]).toVerifySteps();
});

test("categories and filters are loaded when switching from a view without the search panel", async () => {
    // set the pivot view as the default view
    defineParams(
        {
            actions: {
                1: {
                    id: 1,
                    name: "Partners",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [
                        [false, "pivot"],
                        [false, "kanban"],
                        [false, "list"],
                    ],
                },
            },
        },
        "replace"
    );

    onRpc("*", (route, { method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(method);
        }
    });
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect([]).toVerifySteps();

    await getService("action").switchView("list");
    expect(["search_panel_select_range", "search_panel_select_multi_range"]).toVerifySteps();

    await getService("action").switchView("kanban");
    expect([]).toVerifySteps();
});

test("scroll kanban view with searchpanel and kept scroll position", async () => {
    for (let i = 10; i < 20; i++) {
        Category._records.push({ id: i, name: "Cat " + i });
        for (let j = 0; j < 9; j++) {
            Partner._records.push({
                id: 100 + i * 10 + j,
                foo: `Record ${i * 10 + j}`,
            });
        }
    }

    class WebClientContainer extends Component {
        static props = ["*"];
        static components = { WebClient };
        static template = xml`
            <div class="o_web_client" style="max-height: 300px"><WebClient/></div>
        `;
    }
    await mountWithCleanup(WebClientContainer);
    await getService("action").doAction(1);
    await getService("action").switchView("kanban");

    // simulate a scroll in the kanban view
    queryFirst(`.o_renderer`).scrollTop = 100;
    await getService("action").doAction(2);

    // execute a second action (in which we don't scroll)
    expect(`.o_content`).toHaveProperty("scrollTop", 0);

    // go back using the breadcrumbs
    await contains(`.o_control_panel .breadcrumb a`).click();
    expect(`.o_renderer`).toHaveProperty("scrollTop", 100);
});

test("scroll position is kept when switching between controllers", async () => {
    for (let i = 10; i < 20; i++) {
        Category._records.push({ id: i, name: "Cat " + i });
    }

    class WebClientContainer extends Component {
        static props = ["*"];
        static components = { WebClient };
        static template = xml`
            <div class="o_web_client" style="max-height: 300px"><WebClient/></div>
        `;
    }
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClientContainer);
    await getService("action").doAction(1);
    expect(`.o_kanban_view .o_content`).toHaveCount(1);
    expect(queryFirst(`.o_search_panel`).scrollTop).toBe(0);

    // simulate a scroll in the search panel and switch into list
    scroll(`.o_search_panel`, { y: 100 });
    await animationFrame();
    await getService("action").switchView("list");
    expect(`.o_list_view .o_content`).toHaveCount(1);
    expect(queryFirst(`.o_search_panel`).scrollTop).toBe(100);

    // simulate another scroll and switch back to kanban
    scroll(`.o_search_panel`, { y: 25 });
    await getService("action").switchView("kanban");
    expect(`.o_kanban_view .o_content`).toHaveCount(1);
    expect(queryFirst(`.o_search_panel`).scrollTop).toBe(25);
});

test("search panel is not instantiated in dialogs", async () => {
    Company._records = Array.from(Array(8), (_, i) => ({
        id: i + 1,
        name: `Company${i + 1}`,
    }));
    Company._views = {
        [["list", false]]: /* xml */ `<tree><field name="name"/></tree>`,
        [["search", false]]: /* xml */ `
            <search>
                <field name="name"/>
                <searchpanel>
                    <field name="category_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1, { viewType: "form" });
    await contains(`.o_field_widget[name="company_id"] .dropdown input`).click();
    await contains(`.o_field_widget[name="company_id"] .o_m2o_dropdown_option_search_more`).click();
    expect(`.modal .o_list_view`).toHaveCount(1);
    expect(`.modal .o_search_panel`).toHaveCount(0);
});

test("Reload categories with counters when filter values are selected", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id" enable_counters="1"/>
                    <field name="state" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("*", (route, { method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(method);
        }
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(["search_panel_select_range", "search_panel_select_multi_range"]).toVerifySteps();
    expect(getCategoriesCounter()).toEqual([1, 3]);
    expect(getFiltersCounter()).toEqual([1, 1, 2]);

    await contains(queryAll`.o_search_panel_filter_value:eq(0) input`).click();
    expect(getCategoriesCounter()).toEqual([1]);
    expect(getFiltersCounter()).toEqual([1, 1, 2]);
    expect(["search_panel_select_range", "search_panel_select_multi_range"]).toVerifySteps();
});

test("many2one: select one, expand, hierarchize, counters", async () => {
    Company._records.push(
        { id: 50, name: "agrobeurre", parent_id: 5 },
        { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
    );
    Partner._records[1].company_id = 50;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(1);
    expect(getCategoriesCounter()).toEqual([2, 1]);

    await contains(`.o_search_panel_category_value header:contains(agrolait)`).click();
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(5);
    expect(getCategoriesCounter()).toEqual([2, 1, 1]);
});

test("many2one: select one, no expand, hierarchize, counters", async () => {
    Company._records.push(
        { id: 50, name: "agrobeurre", parent_id: 5 },
        { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
    );
    Partner._records[1].company_id = 50;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(1);
    expect(getCategoriesCounter()).toEqual([2, 1]);

    await contains(`.o_search_panel_category_value header:contains(agrolait)`).click();
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(4);
    expect(getCategoriesCounter()).toEqual([2, 1, 1]);
});

test("many2one: select one, expand, no hierarchize, counters", async () => {
    Company._records.push(
        { id: 50, name: "agrobeurre", parent_id: 5 },
        { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
    );
    Partner._records[1].company_id = 50;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" hierarchize="0" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(5);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getCategoriesCounter()).toEqual([2, 1, 1]);
});

test("many2one: select one, no expand, no hierarchize, counters", async () => {
    Company._records.push(
        { id: 50, name: "agrobeurre", parent_id: 5 },
        { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
    );
    Partner._records[1].company_id = 50;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" hierarchize="0" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(4);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getCategoriesCounter()).toEqual([2, 1, 1]);
});

test("many2one: select one, expand, hierarchize, no counters", async () => {
    Company._records.push(
        { id: 50, name: "agrobeurre", parent_id: 5 },
        { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
    );
    Partner._records[1].company_id = 50;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(1);
    expect(getCategoriesCounter()).toEqual([]);

    await contains(`.o_search_panel_category_value header:contains(agrolait)`).click();
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(5);
    expect(getCategoriesCounter()).toEqual([]);
});

test("many2one: select one, no expand, hierarchize, no counters", async () => {
    Company._records.push(
        { id: 50, name: "agrobeurre", parent_id: 5 },
        { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
    );
    Partner._records[1].company_id = 50;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(1);
    expect(getCategoriesCounter()).toEqual([]);

    await contains(`.o_search_panel_category_value header:contains(agrolait)`).click();
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(4);
    expect(getCategoriesCounter()).toEqual([]);
});

test("many2one: select one, expand, no hierarchize, no counters", async () => {
    Company._records.push(
        { id: 50, name: "agrobeurre", parent_id: 5 },
        { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
    );
    Partner._records[1].company_id = 50;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" hierarchize="0" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(5);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getCategoriesCounter()).toEqual([]);
});

test("many2one: select one, no expand, no hierarchize, no counters", async () => {
    Company._records.push(
        { id: 50, name: "agrobeurre", parent_id: 5 },
        { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
    );
    Partner._records[1].company_id = 50;
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" hierarchize="0"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(4);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getCategoriesCounter()).toEqual([]);
});

test("many2one: select multi, expand, groupby, counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(5);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([2, 2]);
});

test("many2one: select multi, no expand, groupby, counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(4);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([2, 2]);
});

test("many2one: select multi, expand, no groupby, counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([2, 2]);
});

test("many2one: select multi, no expand, no groupby, counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(2);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([2, 2]);
});

test("many2one: select multi, expand, groupby, no counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(5);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

test("many2one: select multi, no expand, groupby, no counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(4);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

test("many2one: select multi, expand, no groupby, no counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

test("many2one: select multi, no expand, no groupby, no counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(2);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

test("many2many: select multi, expand, groupby, counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(5);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([2, 1]);
});

test("many2many: select multi, no expand, groupby, counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" groupby="category_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(4);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([2, 1]);
});

test("many2many: select multi, expand, no groupby, counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([2, 1]);
});

test("many2many: select multi, no expand, no groupby, counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(2);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([2, 1]);
});

test("many2many: select multi, expand, groupby, no counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" groupby="category_id" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(5);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

test("many2many: select multi, no expand, groupby, no counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" groupby="category_id"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(4);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

test("many2many: select multi, expand, no groupby, no counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

test("many2many: select multi, no expand, no groupby, no counters", async () => {
    Company._records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(2);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

test("selection: select one, expand, counters", async () => {
    Partner._records.shift();
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(4);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getCategoriesCounter()).toEqual([1, 2]);
});

test("selection: select one, no expand, counters", async () => {
    Partner._records.shift();
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getCategoriesCounter()).toEqual([1, 2]);
});

test("selection: select one, expand, no counters", async () => {
    Partner._records.shift();
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(4);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getCategoriesCounter()).toEqual([]);
});

test("selection: select one, no expand, no counters", async () => {
    Partner._records.shift();
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_field .o_search_panel_category_value`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getCategoriesCounter()).toEqual([]);
});

test("selection: select multi, expand, counters", async () => {
    Partner._records.shift();
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([1, 2]);
});

test("selection: select multi, no expand, counters", async () => {
    Partner._records.shift();
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(2);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([1, 2]);
});

test("selection: select multi, expand, no counters", async () => {
    Partner._records.shift();
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" select="multi" expand="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(3);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

test("selection: select multi, no expand, no counters", async () => {
    Partner._records.shift();
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" select="multi"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(2);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([]);
});

//-------------------------------------------------------------------------
// Model domain and count domain distinction
//-------------------------------------------------------------------------

test("selection: select multi, no expand, counters, extra_domain", async () => {
    Partner._records.shift();
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id"/>
                    <field name="state" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_label`).toHaveCount(5);
    expect(`.o_toggle_fold > i`).toHaveCount(0);
    expect(getFiltersCounter()).toEqual([1, 2]);

    await contains(`.o_search_panel_category_value header:contains(asustek)`).click();
    expect(`.o_search_panel_label`).toHaveCount(5);
    expect(getFiltersCounter()).toEqual([1]);
});

//-------------------------------------------------------------------------
// Limit
//-------------------------------------------------------------------------

test("reached limit for a category", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" limit="2"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_section`).toHaveCount(1);
    expect(`.o_search_panel_section_header`).toHaveCount(1);
    expect(`.o_search_panel_section_header`).toHaveText("RES.COMPANY");
    expect(`section div.alert.alert-warning`).toHaveCount(1);
    expect(`section div.alert.alert-warning`).toHaveText("Too many items to display.");
    expect(`.o_search_panel_category_value`).toHaveCount(0);
});

test("reached limit for a filter", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" limit="2"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_section`).toHaveCount(1);
    expect(`.o_search_panel_section_header`).toHaveCount(1);
    expect(`.o_search_panel_section_header`).toHaveText("RES.COMPANY");
    expect(`section div.alert.alert-warning`).toHaveCount(1);
    expect(`section div.alert.alert-warning`).toHaveText("Too many items to display.");
    expect(`.o_search_panel_filter_value`).toHaveCount(0);
});

test("a selected value becomming invalid should no more impact the view", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <filter name="filter_on_def" string="DEF" domain="[('state', '=', 'def')]"/>
                <searchpanel>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("*", (route, { method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(method);
        }
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(["search_panel_select_range"]).toVerifySteps();

    // select 'ABC' in search panel
    await contains(`.o_search_panel_category_value header:eq(1)`).click();
    expect(["search_panel_select_range"]).toVerifySteps();

    // select DEF in filter menu
    await toggleSearchBarMenu();
    await toggleMenuItem("DEF");
    expect(["search_panel_select_range"]).toVerifySteps();
    expect(`.o_search_panel_category_value header:eq(0)`).toHaveText("All");
    expect(`.o_search_panel_category_value header:eq(0)`).toHaveClass("active");
});

test("Categories with default attributes should be udpated when external domain changes", async () => {
    Partner._views = {
        search: /* xml */ `
                <search>
                    <filter name="filter_on_def" string="DEF" domain="[('state', '=', 'def')]"/>
                    <searchpanel>
                        <field name="state"/>
                    </searchpanel>
                </search>
            `,
    };

    onRpc("*", (route, { method }) => {
        if (/search_panel_/.test(route)) {
            expect.step(method);
        }
    });
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(["search_panel_select_range"]).toVerifySteps();
    expect(getCategoriesContent()).toEqual(["All", "ABC", "DEF", "GHI"]);

    // select 'ABC' in search panel --> no need to update the category value
    await contains(`.o_search_panel_category_value header:eq(1)`).click();
    expect([]).toVerifySteps();
    expect(getCategoriesContent()).toEqual(["All", "ABC", "DEF", "GHI"]);

    // select DEF in filter menu --> the external domain changes --> the values should be updated
    await toggleSearchBarMenu();
    await toggleMenuItem("DEF");
    expect(["search_panel_select_range"]).toVerifySteps();
    expect(getCategoriesContent()).toEqual(["All", "DEF"]);
});

test("Category with counters and filter with domain", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id"/>
                    <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(getCategoriesContent()).toEqual(["All", "gold", "silver"]);
});

test("Category with counters and filter with domain and context", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id"/>
                    <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]"/>
                </searchpanel>
            </search>
        `,
    };

    onRpc("search_panel_select_range", (_, { kwargs }) => expect.step(kwargs.context.special_key));
    onRpc("search_panel_select_multi_range", (_, { kwargs }) =>
        expect.step(kwargs.context.special_key)
    );
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
        context: {
            special_key: "special_key",
        },
    });
    expect(["special_key", "special_key"]).toVerifySteps();
});

test("Display message when no filter availible", async () => {
    Partner._records = [];
    Company._records = [];
    Category._records = [];

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_empty_state`).toHaveCount(1);
    expect(`.o_search_panel_empty_state button`).toHaveCount(1);
});

test("Don't display empty state message when some filters are available", async () => {
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel_empty_state`).toHaveCount(0);
});

test("search panel can be collapsed/expanded", async () => {
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel`).toHaveCount(1);
    expect(`.o_search_panel_section`).toHaveCount(2);

    await contains(`.o_search_panel button`).click();
    expect(`.o_search_panel`).toHaveCount(0);
    expect(`.o_search_panel_sidebar`).toHaveCount(1);
    expect(`.o_search_panel_sidebar`).toHaveText("All");

    await contains(`.o_search_panel_sidebar button`).click();
    expect(`.o_search_panel`).toHaveCount(1);

    await contains(queryAll`.o_search_panel_category_value header`[1]).click();
    await contains(queryAll`.o_search_panel_filter_value input`[1]).click();
    await contains(`.o_search_panel button`).click();
    expect(`.o_search_panel`).toHaveCount(0);
    expect(`.o_search_panel_sidebar`).toHaveCount(1);
    expect(`.o_search_panel_sidebar`).toHaveText("asusteksilver");
});

test("search panel collapse with multiple filter categories selected", async () => {
    Partner._views = {
        search: /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                    <field name="category_id" select="multi" enable_counters="1"/>
                    <field name="state" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>
        `,
    };

    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });
    expect(`.o_search_panel`).toHaveCount(1);
    expect(`.o_search_panel_section`).toHaveCount(3);

    await contains(queryAll`.o_search_panel_category_value header`[1]).click();
    await contains(queryAll`.o_search_panel_filter_value input`[1]).click();
    await contains(queryAll`.o_search_panel_filter_value input`[2]).click();
    await contains(`.o_search_panel button`).click();
    expect(`.o_search_panel`).toHaveCount(0);
    expect(`.o_search_panel_sidebar`).toHaveCount(1);
    expect(`.o_search_panel_sidebar`).toHaveText("asusteksilverABC");
});

test("search panel should be resizable", async () => {
    await mountWithSearch(TestComponent, {
        resModel: "partner",
        searchViewId: false,
    });

    const searchPanel = queryFirst(".o_search_panel");
    const resizeHandle = queryFirst(".o_search_panel_resize");
    const originalWidth = searchPanel.offsetWidth;

    const { drop } = drag(resizeHandle);
    drop(resizeHandle, { position: { x: 500 } });
    expect(searchPanel.offsetWidth - originalWidth).toBeGreaterThan(0);
});
