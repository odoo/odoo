/** @odoo-module **/

import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import {
    click,
    getFixture,
    legacyExtraNextTick,
    makeDeferred,
    nextTick,
} from "@web/../tests/helpers/utils";
import {
    makeWithSearch,
    setupControlPanelServiceRegistry,
    switchView,
    toggleFilterMenu,
    toggleMenuItem,
} from "@web/../tests/search/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { FilterMenu } from "@web/search/filter_menu/filter_menu";
import { GroupByMenu } from "@web/search/group_by_menu/group_by_menu";
import { SearchPanel } from "@web/search/search_panel/search_panel";

const { Component, xml } = owl;

const serviceRegistry = registry.category("services");

//-----------------------------------------------------------------------------
// Helpers
//-----------------------------------------------------------------------------

const getValues = (el, type) => {
    switch (type) {
        case "category": {
            return [...el.querySelectorAll(".o_search_panel_category_value header")];
        }
        case "filter": {
            return [...el.getElementsByClassName("o_search_panel_filter_value")];
        }
        case "filterGroup": {
            return [...el.getElementsByClassName("o_search_panel_filter_group")];
        }
        case "groupHeader": {
            return [...el.getElementsByClassName("o_search_panel_group_header")];
        }
    }
};

const getValue = (el, type, content = 0, additionalSelector = null) => {
    const values = getValues(el, type);
    let match = null;
    if (Number.isInteger(content) && content < values.length) {
        match = values[content];
    } else {
        const re = new RegExp(content, "i");
        match = values.find((v) => re.test(v.innerText.trim()));
    }
    if (match && additionalSelector) {
        match = match.querySelector(additionalSelector);
    }
    return match;
};

const parseContent = ([value, counter]) => (counter ? `${value}: ${counter}` : value);
const getContent = (el, type, parse = parseContent) => {
    return getValues(el, type)
        .map((v) => parse(v.innerText.trim().split(/\s+/)))
        .filter((v) => v !== null);
};

// Categories
const getCategory = (el, ...args) => getValue(el, "category", ...args);
const getCategoriesContent = (el, ...args) => getContent(el, "category", ...args);

// Filters
const getFilter = (el, ...args) => getValue(el, "filter", ...args);
const getFiltersContent = (el, ...args) => getContent(el, "filter", ...args);

// Filter groups
const getFilterGroup = (el, ...args) => getValue(el, "filterGroup", ...args);
const getFilterGroupContent = (el, ...args) => {
    const group = getFilterGroup(el, ...args);
    return [getContent(group, "groupHeader")[0], getFiltersContent(group)];
};

const getCounters = (v) => (isNaN(v[1]) ? null : Number(v[1]));

const makeTestComponent = ({ onWillStart, onWillUpdateProps } = {}) => {
    let domain;
    class TestComponent extends Component {
        setup() {
            owl.onWillStart(async () => {
                if (onWillStart) {
                    await onWillStart();
                }
                domain = this.props.domain;
            });
            owl.onWillUpdateProps(async (nextProps) => {
                if (onWillUpdateProps) {
                    await onWillUpdateProps();
                }
                domain = nextProps.domain;
            });
        }
    }

    TestComponent.components = { FilterMenu, GroupByMenu, SearchPanel };
    TestComponent.template = xml`
        <div class="o_test_component">
            <SearchPanel t-if="env.searchModel.display.searchPanel" />
            <FilterMenu />
            <GroupByMenu />
        </div>`;

    return { TestComponent, getDomain: () => domain };
};

let serverData;
let target;

QUnit.module("Search", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                        int_field: { string: "Int Field", type: "integer", group_operator: "sum" },
                        company_id: { string: "company", type: "many2one", relation: "company" },
                        company_ids: {
                            string: "Companies",
                            type: "many2many",
                            relation: "company",
                        },
                        category_id: { string: "category", type: "many2one", relation: "category" },
                        state: {
                            string: "State",
                            type: "selection",
                            selection: [
                                ["abc", "ABC"],
                                ["def", "DEF"],
                                ["ghi", "GHI"],
                            ],
                        },
                    },
                    records: [
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
                    ],
                },
                company: {
                    fields: {
                        name: { string: "Display Name", type: "char" },
                        parent_id: {
                            string: "Parent company",
                            type: "many2one",
                            relation: "company",
                        },
                        category_id: { string: "Category", type: "many2one", relation: "category" },
                    },
                    records: [
                        { id: 3, name: "asustek", category_id: 6 },
                        { id: 5, name: "agrolait", category_id: 7 },
                    ],
                },
                category: {
                    fields: {
                        name: { string: "Category Name", type: "char" },
                    },
                    records: [
                        { id: 6, name: "gold" },
                        { id: 7, name: "silver" },
                    ],
                },
            },
            actions: {
                1: {
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
                2: {
                    id: 2,
                    name: "Partners",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                },
            },
            views: {
                "partner,false,toy": /* xml */ `<toy />`,
                "partner,false,list": /* xml */ `
                    <tree>
                        <field name="foo"/>
                    </tree>`,
                "partner,false,kanban": /* xml */ `
                    <kanban>
                        <templates>
                            <div t-name="kanban-box" class="oe_kanban_global_click">
                                <field name="foo"/>
                            </div>
                        </templates>
                    </kanban>`,
                "partner,false,form": /* xml */ `
                    <form>
                        <button name="1" type="action" string="multi view"/>
                        <field name="foo"/>
                        <field name="company_id"/>
                    </form>`,
                "partner,false,pivot": /* xml */ `<pivot><field name="int_field" type="measure"/></pivot>`,
                "partner,false,search": /* xml */ `
                    <search>
                        <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                        <filter name="filter" string="Filter" domain="[('bar', '=', true)]"/>
                        <filter name="true_domain" string="True Domain" domain="[(1, '=', 1)]"/>
                        <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                        <searchpanel view_types="kanban,list,toy">
                            <field name="company_id" enable_counters="1" expand="1"/>
                            <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
        };
        target = getFixture();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("user", makeFakeUserService());
    });

    QUnit.module("SearchPanel");

    QUnit.test("basic rendering of a component without search panel", async (assert) => {
        assert.expect(2);

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { method }) {
                if (/search_panel_/.test(method || route)) {
                    throw new Error("No search panel section should be loaded");
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            display: { searchPanel: false },
        });
        assert.containsNone(target, ".o_search_panel");
        assert.deepEqual(getDomain(), []); // initial domain
    });

    QUnit.test("basic rendering of a component with empty search panel", async (assert) => {
        assert.expect(2);

        serverData.views["partner,false,search"] = `<search><searchpanel /></search>`;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { method, model }) {
                if (/search_panel_/.test(method || route)) {
                    assert.step(`${method || route} on ${model}`);
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsNone(target, ".o_search_panel");
        assert.deepEqual(getDomain(), []); // initial domain
    });

    QUnit.test("basic rendering of a component with search panel", async (assert) => {
        assert.expect(15);
        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { method, model }) {
                if (/search_panel_/.test(method || route)) {
                    assert.step(`${method || route} on ${model}`);
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsOnce(target, ".o_search_panel");
        assert.containsN(target, ".o_search_panel_section", 2);

        const sections = target.querySelectorAll(".o_search_panel_section");

        const firstSection = sections[0];
        assert.hasClass(
            firstSection.querySelector(".o_search_panel_section_header i"),
            "fa-folder"
        );
        assert.containsOnce(firstSection, ".o_search_panel_section_header:contains(company)");
        assert.containsN(firstSection, ".o_search_panel_category_value", 3);
        assert.containsOnce(firstSection, ".o_search_panel_category_value:first .active");
        assert.deepEqual(
            [...firstSection.querySelectorAll(".o_search_panel_category_value")].map((el) =>
                el.innerText.replace(/\s/g, " ")
            ),
            ["All", "asustek 2", "agrolait 2"]
        );

        const secondSection = sections[1];
        assert.hasClass(
            secondSection.querySelector(".o_search_panel_section_header i"),
            "fa-filter"
        );
        assert.containsOnce(secondSection, ".o_search_panel_section_header:contains(category)");
        assert.containsN(secondSection, ".o_search_panel_filter_value", 2);
        assert.deepEqual(
            [...secondSection.querySelectorAll(".o_search_panel_filter_value")].map((el) =>
                el.innerText.replace(/\s/g, " ")
            ),
            ["gold 1", "silver 3"]
        );

        assert.verifySteps([
            "search_panel_select_range on partner",
            "search_panel_select_multi_range on partner",
        ]);
        assert.deepEqual(getDomain(), []); // initial domain (does not need the sections to be loaded)
    });

    QUnit.test("sections with custom icon and color", async (assert) => {
        assert.expect(5);

        const { TestComponent, getDomain } = makeTestComponent();

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel view_types="toy">
                    <field name="company_id" icon="fa-car" color="blue" enable_counters="1"/>
                    <field name="state" select="multi" icon="fa-star" color="#000" enable_counters="1"/>
                </searchpanel>
            </search>`;

        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            config: { viewType: "toy" },
        });

        const sectionHeaderIcons = target.querySelectorAll(".o_search_panel_section_header i");
        assert.hasClass(sectionHeaderIcons[0], "fa-car");
        assert.hasAttrValue(sectionHeaderIcons[0], 'style="{color: blue}"');
        assert.hasClass(sectionHeaderIcons[1], "fa-star");
        assert.hasAttrValue(sectionHeaderIcons[1], 'style="{color: #000}"');

        assert.deepEqual(getDomain(), []);
    });

    QUnit.test('sections with attr invisible="1" are ignored', async (assert) => {
        // 'groups' attributes are converted server-side into invisible="1" when the user doesn't
        // belong to the given group
        assert.expect(3);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                    <field name="state" select="multi" invisible="1" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { method }) {
                if (/search_panel_/.test(method || route)) {
                    assert.step(method || route);
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            config: { viewType: "kanban" },
        });

        assert.containsOnce(target, ".o_search_panel_section");
        assert.verifySteps(["search_panel_select_range"]);
    });

    QUnit.test("categories and filters order is kept", async (assert) => {
        assert.expect(4);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                    <field name="category_id" select="multi" enable_counters="1"/>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            config: { viewType: "kanban" },
        });

        const headers = target.getElementsByClassName("o_search_panel_section_header");
        assert.containsN(target, ".o_search_panel_section", 3);
        assert.strictEqual(headers[0].innerText.trim(), "COMPANY");
        assert.strictEqual(headers[1].innerText.trim(), "CATEGORY");
        assert.strictEqual(headers[2].innerText.trim(), "STATE");
    });

    QUnit.test(
        "specify active category value in context and manually change category",
        async (assert) => {
            assert.expect(4);

            serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>`;

            const { TestComponent, getDomain } = makeTestComponent();
            await makeWithSearch({
                serverData,
                Component: TestComponent,
                resModel: "partner",
                searchViewId: false,
                context: {
                    searchpanel_default_company_id: false,
                    searchpanel_default_state: "ghi",
                },
            });

            assert.deepEqual(
                [
                    ...target.querySelectorAll(
                        ".o_search_panel_category_value header.active label"
                    ),
                ].map((el) => el.innerText),
                ["All", "GHI"]
            );
            assert.deepEqual(getDomain(), [["state", "=", "ghi"]]);

            // select 'ABC' in the category 'state'
            await click(target.querySelectorAll(".o_search_panel_category_value header")[4]);

            assert.deepEqual(
                [
                    ...target.querySelectorAll(
                        ".o_search_panel_category_value header.active label"
                    ),
                ].map((el) => el.innerText),
                ["All", "ABC"]
            );

            assert.deepEqual(getDomain(), [["state", "=", "abc"]]);
        }
    );

    QUnit.test("use category (on many2one) to refine search", async (assert) => {
        assert.expect(10);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            domain: [["bar", "=", true]],
            context: {
                searchpanel_default_company_id: false,
                searchpanel_default_state: "ghi",
            },
        });

        assert.deepEqual(getDomain(), [["bar", "=", true]]);

        // select "asustek"
        await click(target.querySelectorAll(".o_search_panel_category_value header")[1]);

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(1) .active");

        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "child_of", 3]]);

        // select "agrolait"
        await click(target.querySelectorAll(".o_search_panel_category_value header")[2]);

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(2) .active");

        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "child_of", 5]]);

        // select "All"
        await click(target.querySelector(".o_search_panel_category_value header"));

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");

        assert.deepEqual(getDomain(), [["bar", "=", true]]);
    });

    QUnit.test("use category (on selection) to refine search", async (assert) => {
        assert.expect(10);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.deepEqual(getDomain(), []);

        // select 'abc'
        await click(target, ".o_search_panel_category_value:nth-of-type(2) header");

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth-of-type(2) .active");

        assert.deepEqual(getDomain(), [["state", "=", "abc"]]);

        // select 'ghi'
        await click(target, ".o_search_panel_category_value:nth-of-type(4) header");

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth-of-type(4) .active");

        assert.deepEqual(getDomain(), [["state", "=", "ghi"]]);

        // select 'All' again
        await click(target, ".o_search_panel_category_value:nth-of-type(1) header");

        assert.containsOnce(target, ".o_search_panel_category_value:nth-of-type(1) .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");

        assert.deepEqual(getDomain(), []);
    });

    QUnit.test("category has been archived", async (assert) => {
        assert.expect(2);

        serverData.models.company.fields.active = { type: "boolean", string: "Archived" };
        serverData.models.company.records = [
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
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(
            target,
            ".o_search_panel_category_value",
            2,
            "The number of categories should be 2: All and Company 5"
        );

        assert.containsNone(
            target,
            ".o_toggle_fold > i",
            "None of the categories should have children"
        );
    });

    QUnit.test("use two categories to refine search", async (assert) => {
        assert.expect(7);

        serverData.views["partner,false,search"] = /* xml */ `
        <search>
            <searchpanel>
                <field name="company_id" enable_counters="1"/>
                <field name="state" enable_counters="1"/>
            </searchpanel>
        </search>
    `;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            domain: [["bar", "=", true]],
        });

        assert.deepEqual(getDomain(), [["bar", "=", true]]);

        assert.containsN(target, ".o_search_panel_section", 2);

        // select 'asustek'
        await click(
            [
                ...target.querySelectorAll(
                    ".o_search_panel_category_value header .o_search_panel_label_title"
                ),
            ].find((el) => el.innerText === "asustek")
        );
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "child_of", 3]]);

        // select 'abc'
        await click(
            [
                ...target.querySelectorAll(
                    ".o_search_panel_category_value header .o_search_panel_label_title"
                ),
            ].find((el) => el.innerText === "ABC")
        );
        assert.deepEqual(getDomain(), [
            "&",
            ["bar", "=", true],
            "&",
            ["company_id", "child_of", 3],
            ["state", "=", "abc"],
        ]);

        // select 'ghi'
        await click(
            [
                ...target.querySelectorAll(
                    ".o_search_panel_category_value header .o_search_panel_label_title"
                ),
            ].find((el) => el.innerText === "GHI")
        );
        assert.deepEqual(getDomain(), [
            "&",
            ["bar", "=", true],
            "&",
            ["company_id", "child_of", 3],
            ["state", "=", "ghi"],
        ]);

        // select 'All' in first category (company_id)
        let firstSection = target.querySelector(".o_search_panel_section");
        await click(firstSection.querySelector(".o_search_panel_category_value header"));
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["state", "=", "ghi"]]);

        firstSection = target.querySelectorAll(".o_search_panel_section")[1];
        // select 'All' in second category (state)
        await click(firstSection.querySelector(".o_search_panel_category_value header"));
        assert.deepEqual(getDomain(), [["bar", "=", true]]);
    });

    QUnit.test("category with parent_field", async (assert) => {
        assert.expect(25);

        serverData.models.company.records.push(
            { id: 40, name: "child company 1", parent_id: 5 },
            { id: 41, name: "child company 2", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 40;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        // 'All' is selected by default
        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");
        assert.containsN(target, ".o_search_panel_category_value", 3);
        assert.containsOnce(target, ".o_search_panel_category_value .o_toggle_fold > i");

        // unfold parent category and select 'All' again
        await click(getCategory(target, 2));
        await click(getCategory(target, 0));

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");
        assert.containsN(target, ".o_search_panel_category_value", 5);
        assert.containsN(
            target,
            ".o_search_panel_category_value .o_search_panel_category_value",
            2
        );

        assert.deepEqual(getDomain(), []);

        // click on first child company
        await click(getCategory(target, 3));

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(
            target,
            ".o_search_panel_category_value .o_search_panel_category_value:first .active"
        );

        assert.deepEqual(getDomain(), [["company_id", "child_of", 40]]);

        // click on parent company
        await click(getCategory(target, 2));

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(2) .active");

        assert.deepEqual(getDomain(), [["company_id", "child_of", 5]]);

        // fold parent company by clicking on it
        await click(getCategory(target, 2));

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(2) .active");

        // parent company should be folded
        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(2) .active");
        assert.containsN(target, ".o_search_panel_category_value", 3);

        assert.deepEqual(getDomain(), [["company_id", "child_of", 5]]);

        // fold category with children
        await click(getCategory(target, 2));
        await click(getCategory(target, 2));

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(2) .active");
        assert.containsN(target, ".o_search_panel_category_value", 3);

        assert.deepEqual(getDomain(), [["company_id", "child_of", 5]]);
    });

    QUnit.test("category with no parent_field", async (assert) => {
        assert.expect(7);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id" enable_counters="1"/>
                </searchpanel>
            </search>
        `;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.deepEqual(getDomain(), []);

        // 'All' is selected by default
        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");
        assert.containsN(target, ".o_search_panel_category_value", 3);

        // click on 'gold' category
        await click(target.querySelectorAll(".o_search_panel_category_value header")[1]);

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(1) .active");

        assert.deepEqual(getDomain(), [["category_id", "=", 6]]); // must use '=' operator (instead of 'child_of')
    });

    QUnit.test("can (un)fold parent category values", async (assert) => {
        assert.expect(7);

        serverData.models.company.records.push(
            { id: 40, name: "child company 1", parent_id: 5 },
            { id: 41, name: "child company 2", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 40;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsOnce(
            target,
            ".o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i"
        );
        assert.hasClass(getCategory(target, "agrolait", ".o_toggle_fold > i"), "fa-caret-right");
        assert.containsN(target, ".o_search_panel_category_value", 3);

        // unfold agrolait
        await click(getCategory(target, "agrolait", ".o_toggle_fold > i"));
        assert.hasClass(getCategory(target, "agrolait", ".o_toggle_fold > i"), "fa-caret-down");
        assert.containsN(target, ".o_search_panel_category_value", 5);

        // fold agrolait
        await click(getCategory(target, "agrolait", ".o_toggle_fold > i"));
        assert.hasClass(getCategory(target, "agrolait", ".o_toggle_fold > i"), "fa-caret-right");
        assert.containsN(target, ".o_search_panel_category_value", 3);
    });

    QUnit.test("fold status is kept at reload", async (assert) => {
        assert.expect(4);

        serverData.models.company.records.push(
            { id: 40, name: "child company 1", parent_id: 5 },
            { id: 41, name: "child company 2", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 40;

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="True Domain" domain="[(1, '=', 1)]"/>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>
        `;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        // unfold agrolait
        function getAgrolaitElement() {
            return [
                ...target.querySelectorAll(".o_search_panel_category_value > header"),
            ].find((el) => el.innerText.includes("agrolait"));
        }

        await click(getAgrolaitElement());
        assert.hasClass(
            getAgrolaitElement().querySelector(".o_toggle_fold > i"),
            "fa-caret-down",
            "'agrolait' should be open"
        );
        assert.containsN(target, ".o_search_panel_category_value", 5);

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "True Domain");

        assert.hasClass(
            getAgrolaitElement().querySelector(".o_toggle_fold > i"),
            "fa-caret-down",
            "'agrolait' should be open"
        );
        assert.containsN(target, ".o_search_panel_category_value", 5);
    });

    QUnit.test("concurrency: delayed component update", async (assert) => {
        assert.expect(15);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>`;

        let promise = makeDeferred();
        const { TestComponent, getDomain } = makeTestComponent({
            onWillUpdateProps: () => promise,
        });
        await makeWithSearch({
            serverData,
            async mockRPC(route) {
                if (route === "/web/dataset/search_read") {
                    await promise;
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            domain: [["bar", "=", true]],
        });

        // 'All' should be selected by default
        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");

        assert.deepEqual(getDomain(), [["bar", "=", true]]);

        // select 'asustek' (delay the reload)
        const asustekPromise = promise;
        await click(getCategory(target, 1));

        // 'asustek' should not be selected yet, and there should still be 3 records
        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");

        assert.deepEqual(getDomain(), [["bar", "=", true]]);

        // select 'agrolait' (delay the reload)
        promise = makeDeferred();
        const agrolaitPromise = promise;
        await click(getCategory(target, 2));

        // 'agrolait' should not be selected yet, and there should still be 3 records
        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");

        assert.deepEqual(getDomain(), [["bar", "=", true]]);

        // unlock asustek search (should be ignored, so there should still be 3 records)
        asustekPromise.resolve();
        await nextTick();

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");

        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "child_of", 3]]);

        // unlock agrolait search, there should now be 1 record
        agrolaitPromise.resolve();
        await nextTick();

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(2) .active");

        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "child_of", 5]]);
    });

    QUnit.test("concurrency: single category", async (assert) => {
        assert.expect(10);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '=', 1)]"/>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>`;

        let promise = makeDeferred();
        const { TestComponent } = makeTestComponent();
        const compPromise = makeWithSearch({
            serverData,
            async mockRPC(route, { method }) {
                await promise;
                assert.step(method || route);
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            context: {
                searchpanel_default_company_id: [5],
            },
        });

        // Case 1: search panel is awaited to build the query with search defaults
        await nextTick();
        assert.verifySteps([]);

        promise.resolve();
        await compPromise;

        assert.verifySteps(["get_views", "search_panel_select_range"]);

        // Case 2: search domain changed so we wait for the search panel once again
        promise = makeDeferred();

        await toggleFilterMenu(target);
        await toggleMenuItem(target, 0);

        assert.verifySteps([]);

        promise.resolve();
        await nextTick();

        assert.verifySteps(["search_panel_select_range"]);

        // Case 3: search domain is the same and default values do not matter anymore
        promise = makeDeferred();

        await click(getCategory(target, 1));

        // The search read is executed right away in this case
        assert.verifySteps([]);

        promise.resolve();
        await nextTick();

        assert.verifySteps(["search_panel_select_range"]);
    });

    QUnit.test("concurrency: category and filter", async (assert) => {
        assert.expect(5);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id" enable_counters="1"/>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        let promise = makeDeferred();
        const { TestComponent } = makeTestComponent();
        const compPromise = makeWithSearch({
            serverData,
            async mockRPC(route, { method }) {
                await promise;
                assert.step(method || route);
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            context: {
                searchpanel_default_company_id: [5],
            },
        });

        await nextTick();
        assert.verifySteps([]);

        promise.resolve();
        await compPromise;

        assert.verifySteps([
            "get_views",
            "search_panel_select_range",
            "search_panel_select_multi_range",
        ]);
    });

    QUnit.test("concurrency: category and filter with a domain", async (assert) => {
        assert.expect(5);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id"/>
                    <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]" enable_counters="1"/>
                </searchpanel>
            </search>`;

        let promise = makeDeferred();
        const { TestComponent } = makeTestComponent();
        const compPromise = makeWithSearch({
            serverData,
            async mockRPC(route, { method }) {
                await promise;
                assert.step(method || route);
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        await nextTick();
        assert.verifySteps([]);

        promise.resolve();
        await compPromise;

        assert.verifySteps([
            "get_views",
            "search_panel_select_range",
            "search_panel_select_multi_range",
        ]);
    });

    QUnit.test("concurrency: misordered get_filters", async (assert) => {
        assert.expect(15);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" enable_counters="1"/>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        let promise;
        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { method }) {
                if (method === "search_panel_select_multi_range") {
                    await promise;
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");

        assert.deepEqual(getDomain(), []);

        // select 'abc' (delay the reload)
        promise = makeDeferred();
        const abcDef = promise;
        await click(getCategory(target, 1));

        // 'All' should still be selected
        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");

        assert.deepEqual(getDomain(), [["state", "=", "abc"]]);

        // select 'ghi' (delay the reload)
        promise = makeDeferred();
        const ghiDef = promise;
        await click(getCategory(target, 3));

        // 'All' should still be selected
        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");

        assert.deepEqual(getDomain(), [["state", "=", "ghi"]]);

        // unlock ghi search
        ghiDef.resolve();
        await nextTick();

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(3) .active");

        assert.deepEqual(getDomain(), [["state", "=", "ghi"]]);

        // unlock abc search (should be ignored)
        abcDef.resolve();
        await nextTick();

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(3) .active");

        assert.deepEqual(getDomain(), [["state", "=", "ghi"]]);
    });

    QUnit.test("concurrency: delayed get_filter", async (assert) => {
        assert.expect(3);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '=', 1)]"/>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        let promise;
        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { method }) {
                if (method === "search_panel_select_multi_range") {
                    await promise;
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.deepEqual(getDomain(), []);

        // trigger a reload and delay the get_filter
        promise = makeDeferred();

        await toggleFilterMenu(target);
        await toggleMenuItem(target, 0);

        assert.deepEqual(getDomain(), []);

        promise.resolve();
        await nextTick();

        assert.deepEqual(getDomain(), [["id", "=", 1]]);
    });

    QUnit.test("use filter (on many2one) to refine search", async (assert) => {
        assert.expect(16);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '=', 1)]"/>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            domain: [["bar", "=", true]],
        });

        assert.containsN(target, ".o_search_panel_filter_value", 2);
        assert.containsNone(target, ".o_search_panel_filter_value input:checked");
        assert.deepEqual(getFiltersContent(target), ["asustek: 2", "agrolait: 1"]);
        assert.deepEqual(getDomain(), [["bar", "=", true]]);

        // check 'asustek'
        await click(getFilter(target, 0, "input"));

        assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
        assert.deepEqual(getFiltersContent(target), ["asustek: 2", "agrolait: 1"]);
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "in", [3]]]);

        // check 'agrolait'
        await click(getFilter(target, 1, "input"));

        assert.containsN(target, ".o_search_panel_filter_value input:checked", 2);
        assert.deepEqual(getFiltersContent(target), ["asustek: 2", "agrolait: 1"]);
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "in", [3, 5]]]);

        // uncheck 'asustek'
        await click(getFilter(target, 0, "input"));

        assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
        assert.deepEqual(getFiltersContent(target), ["asustek: 2", "agrolait: 1"]);
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "in", [5]]]);

        // uncheck 'agrolait'
        await click(getFilter(target, 1, "input"));

        assert.containsNone(target, ".o_search_panel_filter_value input:checked");
        assert.deepEqual(getFiltersContent(target), ["asustek: 2", "agrolait: 1"]);
        assert.deepEqual(getDomain(), [["bar", "=", true]]);
    });

    QUnit.test("use filter (on selection) to refine search", async (assert) => {
        assert.expect(16);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '=', 1)]"/>
                <searchpanel>
                    <field name="state" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            domain: [["bar", "=", true]],
        });

        assert.containsN(target, ".o_search_panel_filter_value", 3);
        assert.containsNone(target, ".o_search_panel_filter_value input:checked");
        assert.deepEqual(getFiltersContent(target), ["ABC: 1", "DEF: 1", "GHI: 1"]);
        assert.deepEqual(getDomain(), [["bar", "=", true]]);

        // check 'abc'
        await click(getFilter(target, 0, "input"));

        assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
        assert.deepEqual(getFiltersContent(target), ["ABC: 1", "DEF: 1", "GHI: 1"]);
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["state", "in", ["abc"]]]);

        // check 'def'
        await click(getFilter(target, 1, "input"));

        assert.containsN(target, ".o_search_panel_filter_value input:checked", 2);
        assert.deepEqual(getFiltersContent(target), ["ABC: 1", "DEF: 1", "GHI: 1"]);
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["state", "in", ["abc", "def"]]]);

        // uncheck 'abc'
        await click(getFilter(target, 0, "input"));

        assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
        assert.deepEqual(getFiltersContent(target), ["ABC: 1", "DEF: 1", "GHI: 1"]);
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["state", "in", ["def"]]]);

        // uncheck 'def'
        await click(getFilter(target, 1, "input"));

        assert.containsNone(target, ".o_search_panel_filter_value input:checked");
        assert.deepEqual(getFiltersContent(target), ["ABC: 1", "DEF: 1", "GHI: 1"]);
        assert.deepEqual(getDomain(), [["bar", "=", true]]);
    });

    QUnit.test(
        "only reload categories and filters when domains change (counters disabled, selection)",
        async (assert) => {
            assert.expect(7);

            serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '&lt;', 5)]"/>
                <searchpanel>
                    <field name="state" expand="1"/>
                    <field name="company_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
                </search>`;

            const { TestComponent } = makeTestComponent();
            await makeWithSearch({
                serverData,
                async mockRPC(route, { method }) {
                    if (/search_panel_/.test(method || route)) {
                        assert.step(method || route);
                    }
                },
                Component: TestComponent,
                resModel: "partner",
                searchViewId: false,
            });

            assert.verifySteps(["search_panel_select_range", "search_panel_select_multi_range"]);

            // reload with another domain, so the filters should be reloaded
            await toggleFilterMenu(target);
            await toggleMenuItem(target, 0);

            assert.verifySteps(["search_panel_select_multi_range"]);

            // change category value, so the filters should be reloaded
            await click(getCategory(target, 1));

            assert.verifySteps(["search_panel_select_multi_range"]);
        }
    );

    QUnit.test(
        "only reload categories and filters when domains change (counters disabled, many2one)",
        async (assert) => {
            assert.expect(7);

            serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="domain" domain="[('id', '&lt;', 5)]"/>
                <searchpanel>
                    <field name="category_id" expand="1"/>
                    <field name="company_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
                </search>`;

            const { TestComponent } = makeTestComponent();
            await makeWithSearch({
                serverData,
                async mockRPC(route, { method }) {
                    if (/search_panel_/.test(method || route)) {
                        assert.step(method || route);
                    }
                },
                Component: TestComponent,
                resModel: "partner",
                searchViewId: false,
            });

            assert.verifySteps(["search_panel_select_range", "search_panel_select_multi_range"]);

            // reload with another domain, so the filters should be reloaded
            await toggleFilterMenu(target);
            await toggleMenuItem(target, 0);

            assert.verifySteps(["search_panel_select_multi_range"]);

            // change category value, so the filters should be reloaded
            await click(getCategory(target, 1));

            assert.verifySteps(["search_panel_select_multi_range"]);
        }
    );

    QUnit.test("category counters", async (assert) => {
        assert.expect(14);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '&lt;', 3)]"/>
                <searchpanel>
                    <field name="state" enable_counters="1" expand="1"/>
                    <field name="company_id" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { args, method }) {
                if (/search_panel_/.test(method || route)) {
                    assert.step(method || route);
                }
                if (route === "/web/dataset/call_kw/partner/search_panel_select_range") {
                    assert.step(args[0]);
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.verifySteps([
            "search_panel_select_range",
            "state",
            "search_panel_select_range",
            "company_id",
        ]);
        assert.deepEqual(getCategoriesContent(target), [
            "All",
            "ABC: 1",
            "DEF: 1",
            "GHI: 2",
            "All",
            "asustek",
            "agrolait",
        ]);

        // reload with another domain, so the categories 'state' and 'company_id' should be reloaded
        await toggleFilterMenu(target);
        await toggleMenuItem(target, 0);

        assert.verifySteps(["search_panel_select_range", "state"]);
        assert.deepEqual(getCategoriesContent(target), [
            "All",
            "ABC: 1",
            "DEF: 1",
            "GHI",
            "All",
            "asustek",
            "agrolait",
        ]);

        // change category value, so the category 'state' should be reloaded
        await click(getCategory(target, 1));

        assert.verifySteps(["search_panel_select_range", "state"]);
        assert.deepEqual(getCategoriesContent(target), [
            "All",
            "ABC: 1",
            "DEF: 1",
            "GHI",
            "All",
            "asustek",
            "agrolait",
        ]);
    });

    QUnit.test("category selection without counters", async (assert) => {
        assert.expect(8);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="Filter" domain="[('id', '&lt;', 3)]"/>
                <searchpanel>
                    <field name="state" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { args, method }) {
                if (/search_panel_/.test(method || route)) {
                    assert.step(method || route);
                }
                if (route === "/web/dataset/call_kw/partner/search_panel_select_range") {
                    assert.step(args[0]);
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.verifySteps(["search_panel_select_range", "state"]);
        assert.deepEqual(getCategoriesContent(target), ["All", "ABC", "DEF", "GHI"]);

        // reload with another domain, so the category 'state' should be reloaded
        await toggleFilterMenu(target);
        await toggleMenuItem(target, 0);

        assert.verifySteps([]);
        assert.deepEqual(getCategoriesContent(target), ["All", "ABC", "DEF", "GHI"]);

        // change category value, so the category 'state' should be reloaded
        await click(getCategory(target, 1));

        assert.verifySteps([]);
        assert.deepEqual(getCategoriesContent(target), ["All", "ABC", "DEF", "GHI"]);
    });

    QUnit.test("filter with groupby", async (assert) => {
        assert.expect(26);

        serverData.models.company.records.push({ id: 11, name: "camptocamp", category_id: 7 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            domain: [["bar", "=", true]],
        });

        assert.containsN(target, ".o_search_panel_filter_group", 2);
        assert.containsOnce(
            target,
            ".o_search_panel_filter_group:first .o_search_panel_filter_value"
        );
        assert.containsN(
            target,
            ".o_search_panel_filter_group:nth(1) .o_search_panel_filter_value",
            2
        );
        assert.containsNone(target, ".o_search_panel_filter_value input:checked");
        assert.deepEqual(getFilterGroupContent(target, 0), ["gold", ["asustek: 2"]]);
        assert.deepEqual(getFilterGroupContent(target, 1), [
            "silver",
            ["agrolait: 1", "camptocamp"],
        ]);
        assert.deepEqual(getDomain(), [["bar", "=", true]]);

        // check 'asustek'
        await click(getFilter(target, 0, "input"));

        const firstGroupCheckbox = getFilterGroup(target, 0, "header > div > input");

        assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
        assert.strictEqual(
            firstGroupCheckbox.checked,
            true,
            "first group checkbox should be checked"
        );
        assert.deepEqual(getFiltersContent(target), ["asustek: 2", "agrolait", "camptocamp"]);
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "in", [3]]]);

        // check 'agrolait'
        await click(getFilter(target, 1, "input"));

        assert.containsN(target, ".o_search_panel_filter_value input:checked", 2);

        const secondGroupCheckbox = getFilterGroup(target, 1, "header > div > input");

        assert.strictEqual(
            secondGroupCheckbox.checked,
            false,
            "second group checkbox should not be checked"
        );
        assert.strictEqual(
            secondGroupCheckbox.indeterminate,
            true,
            "second group checkbox should be indeterminate"
        );
        assert.deepEqual(getFiltersContent(target), ["asustek", "agrolait", "camptocamp"]);
        assert.deepEqual(getDomain(), [
            "&",
            ["bar", "=", true],
            "&",
            ["company_id", "in", [3]],
            ["company_id", "in", [5]],
        ]);

        // check 'camptocamp'
        await click(getFilter(target, 2, "input"));

        assert.containsN(target, ".o_search_panel_filter_value input:checked", 3);
        assert.strictEqual(
            secondGroupCheckbox.checked,
            true,
            "second group checkbox should be checked"
        );
        assert.strictEqual(
            secondGroupCheckbox.indeterminate,
            false,
            "second group checkbox should not be indeterminate"
        );
        assert.deepEqual(getFiltersContent(target), ["asustek", "agrolait", "camptocamp"]);
        assert.deepEqual(getDomain(), [
            "&",
            ["bar", "=", true],
            "&",
            ["company_id", "in", [3]],
            ["company_id", "in", [5, 11]],
        ]);

        // uncheck second group
        await click(getFilterGroup(target, 1, "header > div > input"));

        assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
        assert.strictEqual(
            secondGroupCheckbox.checked,
            false,
            "second group checkbox should not be checked"
        );
        assert.strictEqual(
            secondGroupCheckbox.indeterminate,
            false,
            "second group checkbox should not be indeterminate"
        );
        assert.deepEqual(getFiltersContent(target), ["asustek: 2", "agrolait", "camptocamp"]);
        assert.deepEqual(getDomain(), ["&", ["bar", "=", true], ["company_id", "in", [3]]]);
    });

    QUnit.test("filter with domain", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 40, name: "child company 1", parent_id: 3 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" domain="[('parent_id','=',False)]" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { kwargs, method }) {
                if (method === "search_panel_select_multi_range") {
                    const toCompare = { ...kwargs, context: {} };
                    assert.deepEqual(toCompare, {
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
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_filter_value", 2);
        assert.deepEqual(getFiltersContent(target), ["asustek: 2", "agrolait: 2"]);
    });

    QUnit.test("filter with domain depending on category", async (assert) => {
        assert.expect(22);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id"/>
                    <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            async mockRPC(route, { kwargs, method }) {
                if (method === "search_panel_select_multi_range") {
                    if (method === "search_panel_select_multi_range") {
                        // the following keys should have same value for all calls to this route
                        const { group_by, search_domain, filter_domain } = kwargs;
                        assert.deepEqual(
                            { group_by, search_domain, filter_domain },
                            {
                                group_by: false,
                                filter_domain: [],
                                search_domain: [],
                            }
                        );
                        assert.step(JSON.stringify(kwargs.category_domain));
                        assert.step(JSON.stringify(kwargs.comodel_domain));
                    }
                }
            },
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        // select 'gold' category
        await click(getCategory(target, 1));

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(1) .active");
        assert.containsOnce(target, ".o_search_panel_filter_value");
        assert.deepEqual(getFiltersContent(target), ["asustek: 1"]);

        // select 'silver' category
        await click(getCategory(target, 2));

        assert.containsOnce(target, ".o_search_panel_category_value:nth(2) .active");
        assert.containsOnce(target, ".o_search_panel_filter_value");
        assert.deepEqual(getFiltersContent(target), ["agrolait: 2"]);

        // select All
        await click(getCategory(target, 0));

        assert.containsOnce(target, ".o_search_panel_category_value:first .active");
        assert.containsNone(target, ".o_search_panel_filter_value");

        assert.verifySteps([
            "[]", // category_domain (All)
            '[["category_id","=",false]]', // comodel_domain (All)
            '[["category_id","=",6]]', // category_domain ('gold')
            '[["category_id","=",6]]', // comodel_domain ('gold')
            '[["category_id","=",7]]', // category_domain ('silver')
            '[["category_id","=",7]]', // comodel_domain ('silver')
            "[]", // category_domain (All)
            '[["category_id","=",false]]', // comodel_domain (All)
        ]);
    });

    QUnit.test("specify active filter values in context", async (assert) => {
        assert.expect(4);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                    <field name="state" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            context: {
                searchpanel_default_company_id: [5],
                searchpanel_default_state: ["abc", "ghi"],
            },
        });

        assert.containsN(target, ".o_search_panel_filter_value input:checked", 3);
        assert.deepEqual(getDomain(), [
            "&",
            ["company_id", "in", [5]],
            ["state", "in", ["abc", "ghi"]],
        ]);

        // manually untick a default value
        await click(getFilter(target, 1, "input"));

        assert.containsN(target, ".o_search_panel_filter_value input:checked", 2);
        assert.deepEqual(getDomain(), [["state", "in", ["abc", "ghi"]]]);
    });

    QUnit.test("retrieved filter value from context does not exist", async (assert) => {
        assert.expect(1);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            context: {
                searchpanel_default_company_id: [1, 3],
            },
        });

        assert.deepEqual(getDomain(), [["company_id", "in", [3]]]);
    });

    QUnit.test("filter with groupby and default values in context", async (assert) => {
        assert.expect(2);

        serverData.models.company.records.push({ id: 11, name: "camptocamp", category_id: 7 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent, getDomain } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            context: {
                searchpanel_default_company_id: [5],
            },
        });

        const secondGroupCheckbox = getFilterGroup(target, 1, "header > div > input");

        assert.strictEqual(secondGroupCheckbox.indeterminate, true);
        assert.deepEqual(getDomain(), [["company_id", "in", [5]]]);
    });

    QUnit.test('Does not confuse false and "false" groupby values', async (assert) => {
        assert.expect(6);

        serverData.models.company.fields.char_field = { string: "Char Field", type: "char" };
        serverData.models.company.records = [
            { id: 3, name: "A", char_field: false },
            { id: 5, name: "B", char_field: "false" },
        ];
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="char_field"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
            context: {
                searchpanel_default_company_id: [5],
            },
        });

        assert.containsOnce(target, ".o_search_panel_section");

        // There should be a group 'false' displayed with only value B inside it.
        assert.containsOnce(target, ".o_search_panel_filter_group");
        assert.deepEqual(getFilterGroupContent(target), ["false", ["B"]]);
        assert.containsOnce(getFilterGroup(target), ".o_search_panel_filter_value");

        // Globally, there should be two values, one displayed in the group 'false', and one at the end of the section
        // (the group false is not displayed and its values are displayed at the first level)
        assert.containsN(target, ".o_search_panel_filter_value", 2);
        assert.deepEqual(getFiltersContent(target), ["B", "A"]);
    });

    QUnit.test("tests conservation of category record order", async (assert) => {
        assert.expect(1);

        serverData.models.company.records.push(
            { id: 56, name: "highID", category_id: 6 },
            { id: 2, name: "lowID", category_id: 6 }
        );
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                    <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.deepEqual(getCategoriesContent(target), [
            "All",
            "lowID",
            "asustek: 2",
            "agrolait: 2",
            "highID",
        ]);
    });

    QUnit.test("search panel is available on list and kanban by default", async (assert) => {
        assert.expect(8);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                <filter name="filter" string="Filter" domain="[('bar', '=', true)]"/>
                <filter name="true_domain" string="True Domain" domain="[(1, '=', 1)]"/>
                <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                    <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const webclient = await createWebClient({ serverData });

        await doAction(webclient, 1);

        assert.containsOnce(target, ".o_kanban_view .o_content.o_component_with_search_panel");
        assert.containsOnce(target, ".o_content.o_component_with_search_panel .o_search_panel");

        await switchView(target, "pivot");

        assert.containsOnce(target, ".o_pivot_view .o_content");
        assert.containsNone(target, ".o_pivot_view .o_content .o_search_panel");

        await switchView(target, "list");
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_list_view .o_content.o_component_with_search_panel");
        assert.containsOnce(target, ".o_content.o_component_with_search_panel .o_search_panel");

        await click(target.querySelector(".o_data_row .o_data_cell"));
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_form_view .o_content");
        assert.containsNone(target, ".o_form_view .o_content .o_search_panel");
    });

    QUnit.test("search panel with view_types attribute", async (assert) => {
        assert.expect(6);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                <filter name="filter" string="Filter" domain="[('bar', '=', true)]"/>
                <filter name="true_domain" string="True Domain" domain="[(1, '=', 1)]"/>
                <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                <searchpanel view_types="kanban,pivot">
                    <field name="company_id" enable_counters="1" expand="1"/>
                    <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const webclient = await createWebClient({ serverData });

        await doAction(webclient, 1);

        assert.containsOnce(target, ".o_kanban_view .o_content.o_component_with_search_panel");
        assert.containsOnce(target, ".o_content.o_component_with_search_panel .o_search_panel");

        await switchView(target, "list");
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_list_view .o_content");
        assert.containsNone(target, ".o_content .o_search_panel");

        await switchView(target, "pivot");

        assert.containsOnce(target, ".o_content.o_component_with_search_panel .o_pivot");
        assert.containsOnce(target, ".o_content.o_component_with_search_panel .o_search_panel");
    });

    QUnit.test("search panel state is shared between views", async (assert) => {
        assert.expect(16);

        const webclient = await createWebClient({
            serverData,
            async mockRPC(route, { kwargs, method }) {
                if (method === "web_search_read") {
                    assert.step(JSON.stringify(kwargs.domain));
                }
            },
        });

        await doAction(webclient, 1);

        assert.hasClass(getCategory(target, 0), "active");
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);

        // select 'asustek' company
        await click(getCategory(target, 1));

        assert.hasClass(getCategory(target, 1), "active");
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 2);

        await switchView(target, "list");

        assert.hasClass(getCategory(target, 1), "active");
        assert.containsN(target, ".o_data_row", 2);

        // select 'agrolait' company
        await click(getCategory(target, 2));

        assert.hasClass(getCategory(target, 2), "active");
        assert.containsN(target, ".o_data_row", 2);

        await switchView(target, "kanban");

        assert.hasClass(getCategory(target, 2), "active");
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 2);

        assert.verifySteps([
            "[]", // initial search_read
            '[["company_id","child_of",3]]', // kanban, after selecting the first company
            '[["company_id","child_of",3]]', // list
            '[["company_id","child_of",5]]', // list, after selecting the other company
            '[["company_id","child_of",5]]', // kanban
        ]);
    });

    QUnit.test("search panel filters are kept between switch views", async (assert) => {
        assert.expect(17);

        const webclient = await createWebClient({
            serverData,
            async mockRPC(route, { kwargs, method }) {
                if (method === "web_search_read") {
                    assert.step(JSON.stringify(kwargs.domain));
                }
            },
        });

        await doAction(webclient, 1);

        assert.containsNone(target, ".o_search_panel_filter_value input:checked");
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);

        // select gold filter
        await click(getFilter(target, 0, "input"));

        assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 1);

        await switchView(target, "list");

        assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
        assert.containsN(target, ".o_data_row", 1);

        // select silver filter
        await click(getFilter(target, 1, "input"));

        assert.containsN(target, ".o_search_panel_filter_value input:checked", 2);
        assert.containsN(target, ".o_data_row", 4);

        await switchView(target, "kanban");

        assert.containsN(target, ".o_search_panel_filter_value input:checked", 2);
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);

        await click(target.querySelector(".o_kanban_record"));
        await click(target.querySelector(".breadcrumb-item"));

        assert.verifySteps([
            "[]", // initial search_read
            '[["category_id","in",[6]]]', // kanban, after selecting the gold filter
            '[["category_id","in",[6]]]', // list
            '[["category_id","in",[6,7]]]', // list, after selecting the silver filter
            '[["category_id","in",[6,7]]]', // kanban
            '[["category_id","in",[6,7]]]', // kanban, after switching back from form view
        ]);
    });

    QUnit.test(
        "search panel filters are kept when switching to a view with no search panel",
        async (assert) => {
            assert.expect(13);

            const webclient = await createWebClient({ serverData });

            await doAction(webclient, 1);

            assert.containsOnce(target, ".o_kanban_view .o_content.o_component_with_search_panel");
            assert.containsOnce(target, ".o_content.o_component_with_search_panel .o_search_panel");
            assert.containsNone(target, ".o_search_panel_filter_value input:checked");
            assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);

            // select gold filter
            await click(getFilter(target, 0, "input"));

            assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
            assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 1);

            // switch to pivot
            await switchView(target, "pivot");

            assert.containsOnce(target, ".o_pivot_view .o_content");
            assert.containsNone(target, ".o_content .o_search_panel");
            assert.strictEqual(target.querySelector(".o_pivot_cell_value").innerText.trim(), "15");

            // switch to list
            await switchView(target, "list");
            await legacyExtraNextTick();

            assert.containsOnce(target, ".o_list_view .o_content.o_component_with_search_panel");
            assert.containsOnce(target, ".o_content.o_component_with_search_panel .o_search_panel");
            assert.containsOnce(target, ".o_search_panel_filter_value input:checked");
            assert.containsN(target, ".o_data_row", 1);
        }
    );

    QUnit.test('after onExecuteAction, selects "All" as default category value', async (assert) => {
        assert.expect(3);

        const webclient = await createWebClient({ serverData });

        await doAction(webclient, 1, { viewType: "form" });
        await click(target.querySelector(".o_form_view .o_form_nosheet button"));

        assert.containsOnce(target, ".o_kanban_view");
        assert.containsOnce(target, ".o_search_panel");
        assert.containsOnce(target, ".o_search_panel_category_value:first .active");
    });

    QUnit.skipWOWL(
        "categories and filters are not reloaded when switching between views",
        async (assert) => {
            assert.expect(3);

            const webclient = await createWebClient({
                serverData,
                async mockRPC(route, { method }) {
                    if (/search_panel_/.test(method || route)) {
                        assert.step(method || route);
                    }
                },
            });

            await doAction(webclient, 1);

            await switchView(target, "list");
            await legacyExtraNextTick();
            await switchView(target, "kanban");
            await legacyExtraNextTick();

            assert.verifySteps([
                "search_panel_select_range", // kanban: categories
                "search_panel_select_multi_range", // kanban: filters
            ]);
        }
    );

    QUnit.test(
        "categories and filters are loaded when switching from a view without the search panel",
        async (assert) => {
            assert.expect(5);

            // set the pivot view as the default view
            serverData.actions[1].views = [
                [false, "pivot"],
                [false, "kanban"],
                [false, "list"],
            ];

            const webclient = await createWebClient({
                serverData,
                async mockRPC(route, { method }) {
                    if (/search_panel_/.test(method || route)) {
                        assert.step(method || route);
                    }
                },
            });

            await doAction(webclient, 1);
            assert.verifySteps([]);

            await switchView(target, "list");
            await legacyExtraNextTick();
            assert.verifySteps(["search_panel_select_range", "search_panel_select_multi_range"]);

            await switchView(target, "kanban");
            await legacyExtraNextTick();
            assert.verifySteps([]);
        }
    );

    QUnit.skipWOWL("scroll position is kept when switching between controllers", async (assert) => {
        assert.expect(6);

        for (let i = 10; i < 20; i++) {
            serverData.models.category.records.push({ id: i, name: "Cat " + i });
        }

        const container = document.createElement("div");
        container.classList.add("o_web_client");
        container.style = "max-height: 300px";
        target.appendChild(container);
        const webclient = await createWebClient({ target: container, serverData });

        await doAction(webclient, 1);

        const getSearchPanel = () => target.querySelector(".o_search_panel");

        assert.containsOnce(target, ".o_kanban_view .o_content");
        assert.strictEqual(getSearchPanel().scrollTop, 0);

        // simulate a scroll in the search panel and switch into list
        getSearchPanel().scrollTo(0, 100);
        await switchView(target, "list");
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_list_view .o_content");
        assert.strictEqual(getSearchPanel().scrollTop, 100);

        // simulate another scroll and switch back to kanban
        getSearchPanel().scrollTo(0, 25);
        await switchView(target, "kanban");
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_kanban_view .o_content");
        assert.strictEqual(getSearchPanel().scrollTop, 25);
    });

    QUnit.skipWOWL("search panel is not instantiated in dialogs", async (assert) => {
        assert.expect(2);

        serverData.models.company.records = Array.from(Array(8), (_, i) => ({
            id: i + 1,
            name: `Company${i + 1}`,
        }));
        serverData.views["company,false,list"] = /* xml */ `<tree><field name="name"/></tree>`;
        serverData.views["company,false,search"] = /* xml */ `
            <search>
                <field name="name"/>
                <searchpanel>
                    <field name="category_id" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const webclient = await createWebClient({ serverData });

        await doAction(webclient, 1, { viewType: "form" });

        await click(target, "[name=company_id] .o_input");
        await click(target, "[name=company_id] .o_input");
        await click(document, ".o_m2o_dropdown_option");
        await legacyExtraNextTick();

        assert.containsOnce(document.body, ".modal .o_list_view");
        assert.containsNone(document.body, ".modal .o_search_panel");
    });

    QUnit.test(
        "Reload categories with counters when filter values are selected",
        async (assert) => {
            assert.expect(10);

            serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id" enable_counters="1"/>
                    <field name="state" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

            const { TestComponent } = makeTestComponent();
            await makeWithSearch({
                serverData,
                async mockRPC(route, { method }) {
                    if (/search_panel_/.test(method || route)) {
                        assert.step(method || route);
                    }
                },
                Component: TestComponent,
                resModel: "partner",
                searchViewId: false,
            });

            assert.verifySteps(["search_panel_select_range", "search_panel_select_multi_range"]);

            assert.deepEqual(getCategoriesContent(target, getCounters), [1, 3]);
            assert.deepEqual(getFiltersContent(target, getCounters), [1, 1, 2]);

            await click(getFilter(target, 0, "input"));

            assert.deepEqual(getCategoriesContent(target, getCounters), [1]);
            assert.deepEqual(getFiltersContent(target, getCounters), [1, 1, 2]);

            assert.verifySteps(["search_panel_select_range", "search_panel_select_multi_range"]);
        }
    );

    QUnit.test("many2one: select one, expand, hierarchize, counters", async (assert) => {
        assert.expect(5);

        serverData.models.company.records.push(
            { id: 50, name: "agrobeurre", parent_id: 5 },
            { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 50;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 3);
        assert.containsOnce(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), [2, 1]);

        await click(getCategory(target, "agrolait"));

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 5);
        assert.deepEqual(getCategoriesContent(target, getCounters), [2, 1, 1]);
    });

    QUnit.test("many2one: select one, no expand, hierarchize, counters", async (assert) => {
        assert.expect(5);

        serverData.models.company.records.push(
            { id: 50, name: "agrobeurre", parent_id: 5 },
            { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 50;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 3);
        assert.containsOnce(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), [2, 1]);

        await click(getCategory(target, "agrolait"));

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 4);
        assert.deepEqual(getCategoriesContent(target, getCounters), [2, 1, 1]);
    });

    QUnit.test("many2one: select one, expand, no hierarchize, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push(
            { id: 50, name: "agrobeurre", parent_id: 5 },
            { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 50;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" hierarchize="0" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 5);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), [2, 1, 1]);
    });

    QUnit.test("many2one: select one, no expand, no hierarchize, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push(
            { id: 50, name: "agrobeurre", parent_id: 5 },
            { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 50;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" hierarchize="0" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 4);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), [2, 1, 1]);
    });

    QUnit.test("many2one: select one, expand, hierarchize, no counters", async (assert) => {
        assert.expect(5);

        serverData.models.company.records.push(
            { id: 50, name: "agrobeurre", parent_id: 5 },
            { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 50;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 3);
        assert.containsOnce(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), []);

        await click(getCategory(target, "agrolait"));

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 5);
        assert.deepEqual(getCategoriesContent(target, getCounters), []);
    });

    QUnit.test("many2one: select one, no expand, hierarchize, no counters", async (assert) => {
        assert.expect(5);

        serverData.models.company.records.push(
            { id: 50, name: "agrobeurre", parent_id: 5 },
            { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 50;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 3);
        assert.containsOnce(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), []);

        await click(getCategory(target, "agrolait"));

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 4);
        assert.deepEqual(getCategoriesContent(target, getCounters), []);
    });

    QUnit.test("many2one: select one, expand, no hierarchize, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push(
            { id: 50, name: "agrobeurre", parent_id: 5 },
            { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 50;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" hierarchize="0" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 5);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), []);
    });

    QUnit.test("many2one: select one, no expand, no hierarchize, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push(
            { id: 50, name: "agrobeurre", parent_id: 5 },
            { id: 51, name: "agrocrèmefraiche", parent_id: 5 }
        );
        serverData.models.partner.records[1].company_id = 50;
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" hierarchize="0"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 4);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), []);
    });

    QUnit.test("many2one: select multi, expand, groupby, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 5);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [2, 2]);
    });

    QUnit.test("many2one: select multi, no expand, groupby, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 4);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [2, 2]);
    });

    QUnit.test("many2one: select multi, expand, no groupby, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 3);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [2, 2]);
    });

    QUnit.test("many2one: select multi, no expand, no groupby, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 2);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [2, 2]);
    });

    QUnit.test("many2one: select multi, expand, groupby, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 5);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    QUnit.test("many2one: select multi, no expand, groupby, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" groupby="category_id"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 4);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    QUnit.test("many2one: select multi, expand, no groupby, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 3);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    QUnit.test("many2one: select multi, no expand, no groupby, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 2);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    QUnit.test("many2many: select multi, expand, groupby, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 5);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [2, 1]);
    });

    QUnit.test("many2many: select multi, no expand, groupby, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" groupby="category_id" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 4);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [2, 1]);
    });

    QUnit.test("many2many: select multi, expand, no groupby, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 3);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [2, 1]);
    });

    QUnit.test("many2many: select multi, no expand, no groupby, counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 2);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [2, 1]);
    });

    QUnit.test("many2many: select multi, expand, groupby, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" groupby="category_id" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 5);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    QUnit.test("many2many: select multi, no expand, groupby, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" groupby="category_id"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 4);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    QUnit.test("many2many: select multi, expand, no groupby, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 3);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    QUnit.test("many2many: select multi, no expand, no groupby, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_ids" select="multi"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 2);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    QUnit.test("selection: select one, expand, counters", async (assert) => {
        assert.expect(3);

        serverData.models.partner.records.shift();
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 4);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), [1, 2]);
    });

    QUnit.test("selection: select one, no expand, counters", async (assert) => {
        assert.expect(3);

        serverData.models.partner.records.shift();
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 3);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), [1, 2]);
    });

    QUnit.test("selection: select one, expand, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.partner.records.shift();
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 4);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), []);
    });

    QUnit.test("selection: select one, no expand, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.partner.records.shift();
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_field .o_search_panel_category_value", 3);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getCategoriesContent(target, getCounters), []);
    });

    QUnit.test("selection: select multi, expand, counters", async (assert) => {
        assert.expect(3);

        serverData.models.partner.records.shift();
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" select="multi" enable_counters="1" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 3);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [1, 2]);
    });

    QUnit.test("selection: select multi, no expand, counters", async (assert) => {
        assert.expect(3);

        serverData.models.partner.records.shift();
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 2);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [1, 2]);
    });

    QUnit.test("selection: select multi, expand, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.partner.records.shift();
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" select="multi" expand="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 3);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    QUnit.test("selection: select multi, no expand, no counters", async (assert) => {
        assert.expect(3);

        serverData.models.partner.records.shift();
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="state" select="multi"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 2);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), []);
    });

    //-------------------------------------------------------------------------
    // Model domain and count domain distinction
    //-------------------------------------------------------------------------

    QUnit.test("selection: select multi, no expand, counters, extra_domain", async (assert) => {
        assert.expect(5);

        serverData.models.partner.records.shift();
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id"/>
                    <field name="state" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsN(target, ".o_search_panel_label", 5);
        assert.containsNone(target, ".o_toggle_fold > i");
        assert.deepEqual(getFiltersContent(target, getCounters), [1, 2]);

        await click(getCategory(target, "asustek"));

        assert.containsN(target, ".o_search_panel_label", 5);
        assert.deepEqual(getFiltersContent(target, getCounters), [1]);
    });

    //-------------------------------------------------------------------------
    // Limit
    //-------------------------------------------------------------------------

    QUnit.test("reached limit for a category", async (assert) => {
        assert.expect(6);
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" limit="2"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsOnce(target, ".o_search_panel_section");
        assert.containsOnce(target, ".o_search_panel_section_header");
        assert.strictEqual(
            target.querySelector(".o_search_panel_section_header").innerText,
            "COMPANY"
        );
        assert.containsOnce(target, "section div.alert.alert-warning");
        assert.strictEqual(
            target.querySelector("section div.alert.alert-warning").innerText,
            "Too many items to display."
        );
        assert.containsNone(target, ".o_search_panel_category_value");
    });

    QUnit.test("reached limit for a filter", async (assert) => {
        assert.expect(6);
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="company_id" select="multi" limit="2"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.containsOnce(target, ".o_search_panel_section");
        assert.containsOnce(target, ".o_search_panel_section_header");
        assert.strictEqual(
            target.querySelector(".o_search_panel_section_header").innerText,
            "COMPANY"
        );
        assert.containsOnce(target, "section div.alert.alert-warning");
        assert.strictEqual(
            target.querySelector("section div.alert.alert-warning").innerText,
            "Too many items to display."
        );
        assert.containsNone(target, ".o_search_panel_filter_value");
    });

    QUnit.test(
        "a selected value becomming invalid should no more impact the view",
        async (assert) => {
            assert.expect(8);
            serverData.views["partner,false,search"] = /* xml */ `
                <search>
                    <filter name="filter_on_def" string="DEF" domain="[('state', '=', 'def')]"/>
                    <searchpanel>
                        <field name="state" enable_counters="1"/>
                    </searchpanel>
                </search>`;

            const { TestComponent } = makeTestComponent();
            await makeWithSearch({
                serverData,
                async mockRPC(route, { method }) {
                    if (/search_panel_/.test(method || route)) {
                        assert.step(method || route);
                    }
                },
                Component: TestComponent,
                resModel: "partner",
                searchViewId: false,
            });

            assert.verifySteps(["search_panel_select_range"]);

            // select 'ABC' in search panel
            await click(getCategory(target, 1));

            assert.verifySteps(["search_panel_select_range"]);

            // select DEF in filter menu
            await toggleFilterMenu(target);
            await toggleMenuItem(target, "DEF");

            assert.verifySteps(["search_panel_select_range"]);

            const firstCategoryValue = getCategory(target, 0);
            assert.strictEqual(firstCategoryValue.innerText, "All");
            assert.hasClass(
                firstCategoryValue,
                "active",
                "the value 'All' should be selected since ABC is no longer a valid value with respect to search domain"
            );
        }
    );

    QUnit.test(
        "Categories with default attributes should be udpated when external domain changes",
        async (assert) => {
            assert.expect(8);

            serverData.views["partner,false,search"] = /* xml */ `
                <search>
                    <filter name="filter_on_def" string="DEF" domain="[('state', '=', 'def')]"/>
                    <searchpanel>
                        <field name="state"/>
                    </searchpanel>
                </search>`;

            const { TestComponent } = makeTestComponent();
            await makeWithSearch({
                serverData,
                async mockRPC(route, { method }) {
                    if (/search_panel_/.test(method || route)) {
                        assert.step(method || route);
                    }
                },
                Component: TestComponent,
                resModel: "partner",
                searchViewId: false,
            });

            assert.verifySteps(["search_panel_select_range"]);
            assert.deepEqual(getCategoriesContent(target), ["All", "ABC", "DEF", "GHI"]);

            // select 'ABC' in search panel --> no need to update the category value
            await click(getCategory(target, 1));

            assert.verifySteps([]);
            assert.deepEqual(getCategoriesContent(target), ["All", "ABC", "DEF", "GHI"]);

            // select DEF in filter menu --> the external domain changes --> the values should be updated
            await toggleFilterMenu(target);
            await toggleMenuItem(target, "DEF");

            assert.verifySteps(["search_panel_select_range"]);
            assert.deepEqual(getCategoriesContent(target), ["All", "DEF"]);
        }
    );

    QUnit.test("Category with counters and filter with domain", async (assert) => {
        assert.expect(1);

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <searchpanel>
                    <field name="category_id"/>
                    <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]"/>
                </searchpanel>
            </search>`;

        const { TestComponent } = makeTestComponent();
        await makeWithSearch({
            serverData,
            Component: TestComponent,
            resModel: "partner",
            searchViewId: false,
        });

        assert.deepEqual(getCategoriesContent(target), ["All", "gold", "silver"]);
    });
});
