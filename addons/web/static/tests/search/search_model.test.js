import { describe, expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { defineModels, fields, models, mountWithSearch } from "@web/../tests/web_test_helpers";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";

describe.current.tags("headless");

class TestComponent extends Component {
    static template = xml`<div class="o_test_component"/>`;
    static props = ["*"];
}

async function createSearchModel(searchProps = {}, config = {}) {
    const component = await mountWithSearch(
        TestComponent,
        {
            resModel: "foo",
            searchViewId: false,
            ...searchProps,
        },
        config
    );
    return component.env.searchModel;
}

function sanitizeSearchItems(model) {
    // We should not access searchItems but there is a problem with getSearchItems:
    // comparisons are not sent back in some cases
    const searchItems = Object.values(model.searchItems);
    return searchItems.map((searchItem) => {
        const copy = Object.assign({}, searchItem);
        delete copy.groupId;
        delete copy.groupNumber;
        delete copy.id;
        return copy;
    });
}

class Foo extends models.Model {
    name = fields.Char();
    foo = fields.Char({ default: "My little Foo Value" });
    date_field = fields.Date({ string: "Date" });
    float_field = fields.Float({ string: "Float" });
    bar = fields.Many2one({ relation: "partner" });
    properties = fields.Properties({
        definition_record: "bar",
        definition_record_field: "child_properties",
    });

    _views = {
        search: `<search/>`,
    };
}

class Partner extends models.Model {
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
        search: `<search/>`,
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

defineModels([Foo, Partner, Company, Category]);

test("parsing empty arch", async () => {
    const model = await createSearchModel();
    expect(sanitizeSearchItems(model)).toEqual([]);
});

test("parsing one field tag", async () => {
    const model = await createSearchModel({
        searchViewArch: `<search><field name="bar"/></search>`,
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Bar",
            fieldName: "bar",
            fieldType: "many2one",
            type: "field",
        },
    ]);
});

test("parsing one separator tag", async () => {
    const model = await createSearchModel({
        searchViewArch: `<search><separator/></search>`,
    });
    expect(sanitizeSearchItems(model)).toEqual([]);
});

test("parsing one separator tag and one field tag", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <separator/>
                <field name="bar"/>
            </search>
        `,
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Bar",
            fieldName: "bar",
            fieldType: "many2one",
            type: "field",
        },
    ]);
});

test("parsing one filter tag", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="filter" string="Hello" domain="[]"/>
            </search>
        `,
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Hello",
            domain: "[]",
            name: "filter",
            type: "filter",
        },
    ]);
});

test("parsing one filter tag with default_period date attribute", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="date_filter" string="Date" date="date_field" default_period="year,year-1"/>
            </search>
        `,
    });
    const dateFilterId = model.getSearchItems((f) => f.type === "dateFilter")[0].id;
    expect(sanitizeSearchItems(model)).toEqual([
        {
            defaultGeneratorIds: ["year", "year-1"],
            description: "Date",
            domain: "[]",
            fieldName: "date_field",
            fieldType: "date",
            type: "dateFilter",
            name: "date_filter",
            optionsParams: {
                customOptions: [],
                endMonth: 0,
                endYear: 0,
                startMonth: -2,
                startYear: -2,
            },
        },
        {
            comparisonOptionId: "previous_period",
            dateFilterId,
            description: "Date: Previous Period",
            type: "comparison",
        },
        {
            comparisonOptionId: "previous_year",
            dateFilterId,
            description: "Date: Previous Year",
            type: "comparison",
        },
    ]);
});

test("parsing date filter with start_month, end_month, start_year, end_year attributes", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter 
                    name="date_filter"
                    string="Date"
                    date="date_field"
                    start_month="-4"
                    end_month="-1"
                    start_year="-1"
                    end_year="3"
                />
            </search>
        `,
    });
    const dateFilterId = model.getSearchItems((f) => f.type === "dateFilter")[0].id;
    expect(sanitizeSearchItems(model)).toEqual([
        {
            defaultGeneratorIds: ["month-1"],
            description: "Date",
            domain: "[]",
            fieldName: "date_field",
            fieldType: "date",
            type: "dateFilter",
            name: "date_filter",
            optionsParams: {
                customOptions: [],
                endMonth: -1,
                endYear: 3,
                startMonth: -4,
                startYear: -1,
            },
        },
        {
            comparisonOptionId: "previous_period",
            dateFilterId,
            description: "Date: Previous Period",
            type: "comparison",
        },
        {
            comparisonOptionId: "previous_year",
            dateFilterId,
            description: "Date: Previous Year",
            type: "comparison",
        },
    ]);
});

test("parsing date filter with custom options", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="date_filter" string="Date" date="date_field">
                    <filter name="birthday_today" string="Today" domain="[('date_field', '=', context_today().strftime('%Y-%m-%d'))]"/>
                    <filter name="birthday_future" string="Future" domain="[('date_field', '>=', context_today().strftime('%Y-%m-%d'))]"/>
                </filter>
            </search>
        `,
    });
    const dateFilterId = model.getSearchItems((f) => f.type === "dateFilter")[0].id;
    expect(sanitizeSearchItems(model)).toEqual([
        {
            defaultGeneratorIds: ["month"],
            description: "Date",
            domain: "[]",
            fieldName: "date_field",
            fieldType: "date",
            name: "date_filter",
            optionsParams: {
                customOptions: [
                    {
                        id: "custom_birthday_today",
                        description: "Today",
                        domain: "[('date_field', '=', context_today().strftime('%Y-%m-%d'))]",
                        type: "dateOption",
                    },
                    {
                        id: "custom_birthday_future",
                        description: "Future",
                        domain: "[('date_field', '>=', context_today().strftime('%Y-%m-%d'))]",
                        type: "dateOption",
                    },
                ],
                endMonth: 0,
                endYear: 0,
                startMonth: -2,
                startYear: -2,
            },
            type: "dateFilter",
        },
        {
            comparisonOptionId: "previous_period",
            dateFilterId,
            description: "Date: Previous Period",
            type: "comparison",
        },
        {
            comparisonOptionId: "previous_year",
            dateFilterId,
            description: "Date: Previous Year",
            type: "comparison",
        },
    ]);
});

test("parsing one filter tag with date attribute ", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="date_filter" string="Date" date="date_field"/>
            </search>
        `,
    });
    const dateFilterId = model.getSearchItems((f) => f.type === "dateFilter")[0].id;
    expect(sanitizeSearchItems(model)).toEqual([
        {
            defaultGeneratorIds: ["month"],
            description: "Date",
            domain: "[]",
            fieldName: "date_field",
            fieldType: "date",
            name: "date_filter",
            optionsParams: {
                customOptions: [],
                endMonth: 0,
                endYear: 0,
                startMonth: -2,
                startYear: -2,
            },
            type: "dateFilter",
        },
        {
            comparisonOptionId: "previous_period",
            dateFilterId,
            description: "Date: Previous Period",
            type: "comparison",
        },
        {
            comparisonOptionId: "previous_year",
            dateFilterId,
            description: "Date: Previous Year",
            type: "comparison",
        },
    ]);
});

test("parsing one groupBy tag", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="groupby" string="Hi" context="{ 'group_by': 'date_field:day'}"/>
            </search>
        `,
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            defaultIntervalId: "day",
            description: "Hi",
            fieldName: "date_field",
            fieldType: "date",
            name: "groupby",
            type: "dateGroupBy",
        },
    ]);
});

test("parsing two filter tags", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="filter_1" string="Hello One" domain="[]"/>
                <filter name="filter_2" string="Hello Two" domain="[('bar', '=', 3)]"/>
            </search>
        `,
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Hello One",
            domain: "[]",
            name: "filter_1",
            type: "filter",
        },
        {
            description: "Hello Two",
            domain: "[('bar', '=', 3)]",
            name: "filter_2",
            type: "filter",
        },
    ]);
});

test("parsing two filter tags separated by a separator", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="filter_1" string="Hello One" domain="[]"/>
                <separator/>
                <filter name="filter_2" string="Hello Two" domain="[('bar', '=', 3)]"/>
            </search>
        `,
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Hello One",
            domain: "[]",
            name: "filter_1",
            type: "filter",
        },
        {
            description: "Hello Two",
            domain: "[('bar', '=', 3)]",
            name: "filter_2",
            type: "filter",
        },
    ]);
});

test("parsing one filter tag and one field", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="filter" string="Hello" domain="[]"/>
                <field name="bar"/>
            </search>
        `,
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Hello",
            domain: "[]",
            name: "filter",
            type: "filter",
        },
        {
            description: "Bar",
            fieldName: "bar",
            fieldType: "many2one",
            type: "field",
        },
    ]);
});

test("parsing two field tags", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <field name="foo"/>
                <field name="bar"/>
            </search>
        `,
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Foo",
            fieldName: "foo",
            fieldType: "char",
            type: "field",
        },
        {
            description: "Bar",
            fieldName: "bar",
            fieldType: "many2one",
            type: "field",
        },
    ]);
});

test("parsing a searchpanel tag", async () => {
    const model = await createSearchModel(
        {
            searchViewArch: `
                <search>
                    <searchpanel/>
                </search>
            `,
        },
        { viewType: "kanban" }
    );
    expect(model.getSections()).toEqual([]);
});

test("parsing a searchpanel field select one", async () => {
    const model = await createSearchModel(
        {
            searchViewArch: `
                <search>
                    <searchpanel>
                        <field name="company_id"/>
                    </searchpanel>
                </search>
            `,
            resModel: "partner",
        },
        { viewType: "kanban" }
    );
    const sections = model.getSections();
    for (const section of sections) {
        section.values = [...section.values];
    }
    expect(sections).toEqual([
        {
            activeValueId: false,
            color: null,
            description: "res.company",
            empty: false,
            enableCounters: false,
            expand: false,
            fieldName: "company_id",
            hierarchize: true,
            icon: "fa-folder",
            id: 1,
            limit: 200,
            parentField: "parent_id",
            rootIds: [false, 3, 5],
            type: "category",
            values: [
                [
                    false,
                    {
                        bold: true,
                        childrenIds: [],
                        display_name: "All",
                        id: false,
                        parentId: false,
                    },
                ],
                [
                    3,
                    {
                        childrenIds: [],
                        display_name: "asustek",
                        id: 3,
                        parentId: false,
                        parent_id: false,
                    },
                ],
                [
                    5,
                    {
                        childrenIds: [],
                        display_name: "agrolait",
                        id: 5,
                        parentId: false,
                        parent_id: false,
                    },
                ],
            ],
        },
    ]);
});

test("parsing a searchpanel field select multi", async () => {
    const model = await createSearchModel(
        {
            searchViewArch: `
                <search>
                    <searchpanel>
                        <field name="company_id" select="multi"/>
                    </searchpanel>
                </search>
            `,
            resModel: "partner",
        },
        { viewType: "kanban" }
    );
    const sections = model.getSections();
    for (const section of sections) {
        section.values = [...section.values];
    }
    expect(sections).toEqual([
        {
            color: null,
            description: "res.company",
            domain: "[]",
            empty: false,
            enableCounters: false,
            expand: false,
            fieldName: "company_id",
            groupBy: null,
            icon: "fa-filter",
            id: 1,
            limit: 200,
            type: "filter",
            values: [
                [
                    3,
                    {
                        checked: false,
                        display_name: "asustek",
                        id: 3,
                    },
                ],
                [
                    5,
                    {
                        checked: false,
                        display_name: "agrolait",
                        id: 5,
                    },
                ],
            ],
        },
    ]);
});

test("parsing a filter and a dateFilter", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="filter" string="Filter" domain="[['foo', '=', 'a']]"/>
                <filter name="date_filter" string="Date" date="date_field"/>
            </search>
        `,
    });
    const groupNumbers = model.getSearchItems(() => true).map((i) => i.groupNumber);
    expect(groupNumbers).toEqual([1, 1]);
});

test("parsing a groupBy and a dateGroupBy", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="group_by" context="{ 'group_by': 'foo'}"/>
                <filter name="date_groupBy" string="DateGroupBy" context="{'group_by': 'date_field:day'}"/>
            </search>
        `,
    });
    const groupNumbers = model.getSearchItems(() => true).map((i) => i.groupNumber);
    expect(groupNumbers).toEqual([1, 1]);
});

test("parsing a filter and a groupBy", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="filter" string="Filter" domain="[['foo', '=', 'a']]"/>
                <filter name="group_by" context="{ 'group_by': 'foo'}"/>
            </search>
        `,
    });
    const groupNumbers = model.getSearchItems(() => true).map((i) => i.groupNumber);
    expect(groupNumbers).toEqual([1, 2]);
});

test("parsing a groupBy and a filter", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="group_by" context="{ 'group_by': 'foo'}"/>
                <filter name="filter" string="Filter" domain="[['foo', '=', 'a']]"/>
            </search>
        `,
    });
    const groupNumbers = model.getSearchItems(() => true).map((i) => i.groupNumber);
    expect(groupNumbers).toEqual([2, 1]);
});

test("process search default group by", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="group_by" context="{ 'group_by': 'foo'}"/>
            </search>
        `,
        context: { search_default_group_by: 14 },
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            defaultRank: 14,
            description: "Foo",
            fieldName: "foo",
            fieldType: "char",
            name: "group_by",
            type: "groupBy",
            isDefault: true,
        },
    ]);
});

test("process and toggle a field with a context to evaluate", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <field name="foo" context="{ 'a': self }"/>
            </search>
        `,
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            context: "{ 'a': self }",
            description: "Foo",
            fieldName: "foo",
            fieldType: "char",
            type: "field",
        },
    ]);
    model.addAutoCompletionValues(1, { label: "7", operator: "=", value: 7 });
    expect(model.context).toEqual({
        a: [7],
        lang: "en",
        tz: "taht",
        uid: 7,
        allowed_company_ids: [1],
    });
});

test("process favorite filters", async () => {
    const model = await createSearchModel({
        irFilters: [
            {
                user_id: [2, "Mitchell Admin"],
                name: "Sorted filter",
                id: 5,
                context: `{"group_by":["foo","bar"]}`,
                sort: '["foo", "-bar"]',
                domain: "[('user_id', '=', uid)]",
                is_default: false,
                model_id: "res.partner",
                action_id: false,
            },
        ],
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            context: {},
            description: "Sorted filter",
            domain: "[('user_id', '=', uid)]",
            groupBys: ["foo", "bar"],
            orderBy: [
                {
                    asc: true,
                    name: "foo",
                },
                {
                    asc: false,
                    name: "bar",
                },
            ],
            removable: true,
            serverSideId: 5,
            type: "favorite",
            userId: 2,
        },
    ]);
});

test("process dynamic filters", async () => {
    const model = await createSearchModel({
        dynamicFilters: [
            {
                description: "Quick search",
                domain: [["id", "in", [1, 3, 4]]],
            },
        ],
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Quick search",
            domain: [["id", "in", [1, 3, 4]]],
            isDefault: true,
            type: "filter",
        },
    ]);
});

test("process a dynamic filter with a isDefault key to false", async () => {
    const model = await createSearchModel({
        dynamicFilters: [
            {
                description: "Quick search",
                domain: [],
                is_default: false,
            },
        ],
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Quick search",
            domain: [],
            isDefault: false,
            type: "filter",
        },
    ]);
});

test("toggle a filter", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="filter" string="Filter" domain="[['foo', '=', 'a']]"/>
            </search>
        `,
    });
    const filterId = Object.keys(model.searchItems).map((key) => Number(key))[0];
    expect(model.domain).toEqual([]);
    model.toggleSearchItem(filterId);
    expect(model.domain).toEqual([["foo", "=", "a"]]);
    model.toggleSearchItem(filterId);
    expect(model.domain).toEqual([]);
});

test("toggle a date filter", async () => {
    mockDate("2019-01-06T15:00:00");
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="date_filter" date="date_field" string="DateFilter"/>
            </search>
        `,
    });
    const filterId = Object.keys(model.searchItems).map((key) => Number(key))[0];
    model.toggleDateFilter(filterId);
    expect(model.domain).toEqual([
        "&",
        ["date_field", ">=", "2019-01-01"],
        ["date_field", "<=", "2019-01-31"],
    ]);
    model.toggleDateFilter(filterId, "first_quarter");
    expect(model.domain).toEqual([
        "|",
        "&",
        ["date_field", ">=", "2019-01-01"],
        ["date_field", "<=", "2019-01-31"],
        "&",
        ["date_field", ">=", "2019-01-01"],
        ["date_field", "<=", "2019-03-31"],
    ]);
    model.toggleDateFilter(filterId, "year");
    expect(model.domain).toEqual([]);
});

test("toggle a custom option in a date filter", async () => {
    mockDate("2019-01-06T15:00:00");
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="date_filter" date="date_field" string="DateFilter">
                    <filter name="today" string="Today" domain="[('date_field', '=', context_today().strftime('%Y-%m-%d'))]"/>
                </filter>
            </search>
        `,
    });
    const filterId = Object.keys(model.searchItems).map((key) => Number(key))[0];
    model.toggleDateFilter(filterId);
    expect(model.domain).toEqual([
        "&",
        ["date_field", ">=", "2019-01-01"],
        ["date_field", "<=", "2019-01-31"],
    ]);
    model.toggleDateFilter(filterId, "custom_today");
    expect(model.domain).toEqual([["date_field", "=", "2019-01-06"]]);
});

test("toggle a date filter with a domain", async () => {
    mockDate("2019-01-06T15:00:00");
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="date_filter" date="date_field" string="DateFilter" domain="[('float_field', '>=', '0')]"/>
            </search>
        `,
    });
    const filterId = Object.keys(model.searchItems).map((key) => Number(key))[0];
    expect(model.domain).toEqual([]);
    model.toggleDateFilter(filterId);
    expect(model.domain).toEqual([
        "&",
        "&",
        ["date_field", ">=", "2019-01-01"],
        ["date_field", "<=", "2019-01-31"],
        ["float_field", ">=", "0"],
    ]);
});

test("toggle a custom option in a date filter with a domain", async () => {
    mockDate("2019-01-06T15:00:00");
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="date_filter" date="date_field" string="DateFilter" domain="[('float_field', '>=', '0')]">
                    <filter name="today" string="Today" domain="[('date_field', '=', context_today().strftime('%Y-%m-%d'))]"/>
                </filter>
            </search>
        `,
    });
    const filterId = Object.keys(model.searchItems).map((key) => Number(key))[0];
    model.toggleDateFilter(filterId, "custom_today");
    expect(model.domain).toEqual([
        "&",
        ["date_field", "=", "2019-01-06"],
        ["float_field", ">=", "0"],
    ]);
});

test("toggle a groupBy", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="groupBy" string="GroupBy" context="{'group_by': 'foo'}"/>
            </search>
        `,
    });
    const filterId = Object.keys(model.searchItems).map((key) => Number(key))[0];
    expect(model.groupBy).toEqual([]);
    model.toggleSearchItem(filterId);
    expect(model.groupBy).toEqual(["foo"]);
    model.toggleSearchItem(filterId);
    expect(model.groupBy).toEqual([]);
});

test("toggle a date groupBy", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="date_groupBy" string="DateGroupBy" context="{'group_by': 'date_field:day'}"/>
            </search>
        `,
    });
    const filterId = Object.keys(model.searchItems).map((key) => Number(key))[0];
    expect(model.groupBy).toEqual([]);
    model.toggleDateGroupBy(filterId);
    expect(model.groupBy).toEqual(["date_field:day"]);
    model.toggleDateGroupBy(filterId, "week");
    expect(model.groupBy).toEqual(["date_field:week", "date_field:day"]);
    model.toggleDateGroupBy(filterId);
    expect(model.groupBy).toEqual(["date_field:week"]);
    model.toggleDateGroupBy(filterId, "week");
    expect(model.groupBy).toEqual([]);
});

test("create a new groupBy", async () => {
    const model = await createSearchModel();
    model.createNewGroupBy("foo");
    expect(sanitizeSearchItems(model)).toEqual([
        {
            custom: true,
            description: "Foo",
            fieldName: "foo",
            fieldType: "char",
            type: "groupBy",
        },
    ]);
    expect(model.groupBy).toEqual(["foo"]);
});

test("create a new dateGroupBy", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="foo" string="Foo" context="{'group_by': 'foo'}"/>
            </search>
        `,
    });
    model.createNewGroupBy("date_field");
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Foo",
            fieldName: "foo",
            fieldType: "char",
            name: "foo",
            type: "groupBy",
        },
        {
            custom: true,
            defaultIntervalId: "month",
            description: "Date",
            fieldName: "date_field",
            fieldType: "date",
            type: "dateGroupBy",
        },
    ]);
    expect(model.groupBy).toEqual(["date_field:month"]);
});

test("dynamic domains evaluation", async () => {
    mockDate("2021-09-17T10:00:00");
    mockTimeZone(2);

    const searchViewArch = `
        <search>
            <filter name="filter_0" domain="[('datetime', '=', (datetime.datetime.combine(context_today(), datetime.time(0,0,0)).to_utc()))]"/>
            <filter name="filter_1" domain="[('date', '=',  context_today() + relativedelta(days=-365))]"/>
            <filter name="filter_2" domain="[('create_date', '&gt;', (context_today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d'))]"/>
            <filter name="filter_3" domain="[('date_deadline', '&lt;', current_date)]"/>
        </search>
    `;

    const evaluatedDomains = [
        [["datetime", "=", "2021-09-16 22:00:00"]],
        [["date", "=", "2020-09-17"]],
        [["create_date", ">", "2021-09-16"]],
        [["date_deadline", "<", "2021-09-17"]],
    ];

    const model = await createSearchModel({
        searchViewArch,
    });
    for (let i = 0; i < evaluatedDomains.length; i++) {
        model.toggleSearchItem(i + 1);
        expect(model.domain).toEqual(evaluatedDomains[i]);
        model.toggleSearchItem(i + 1);
    }
});

test("dynamic domains evaluation using global context", async () => {
    const searchViewArch = `
        <search>
            <filter name="filter" domain="[('date_deadline', '&lt;', context.get('my_date'))]"/>
        </search>
    `;

    const model = await createSearchModel({
        searchViewArch,
        context: {
            my_date: "2021-09-17",
        },
    });

    model.toggleSearchItem(1);
    expect(model.domain).toEqual([["date_deadline", "<", "2021-09-17"]]);
});

test("field tags with invisible attribute", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <field name="foo" invisible="context.get('abc')"/>
                <field name="bar" invisible="context.get('def')"/>
                <field name="float_field" invisible="1"/>
            </search>
        `,
        context: { abc: true },
    });
    const fields = model.getSearchItems((f) => f.type === "field").map((item) => item.fieldName);
    expect(fields).toEqual(["bar"]);
});

test("filter tags with invisible attribute", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="filter1" string="Invisible ABC" domain="[]" invisible="context.get('abc')"/>
                <filter name="filter2" string="Invisible DEF" domain="[]" invisible="context.get('def')"/>
                <filter name="filter3" string="Always invisible" domain="[]" invisible="1"/>
            </search>
        `,
        context: { abc: true },
    });
    const filters = model
        .getSearchItems((item) => ["filter", "dateFilter"].includes(item.type))
        .map((item) => item.name);
    expect(filters).toEqual(["filter2"]);
});

test("no search items created for search panel sections", async () => {
    const model = await createSearchModel(
        {
            searchViewArch: `
                <search>
                    <searchpanel>
                        <field name="company_id"/>
                        <field name="company_id" select="multi"/>
                    </searchpanel>
                </search>
            `,
            resModel: "partner",
        },
        { viewType: "kanban" }
    );
    const sections = model.getSections();
    expect(sections).toHaveLength(2);
    expect(sanitizeSearchItems(model)).toEqual([]);
});

test("a field of type 'properties' should not be accepted as a search_default", async () => {
    const searchViewArch = `
        <search>
            <field name="properties"/>
        </search>
    `;

    const model = await createSearchModel({
        searchViewArch,
        context: {
            search_default_properties: true,
        },
    });
    expect(sanitizeSearchItems(model)).toEqual([
        {
            description: "Properties",
            fieldName: "properties",
            fieldType: "properties",
            type: "field",
        },
    ]);
});

test("allow filtering based on extra keys in getSearchItems", async () => {
    const model = await createSearchModel({
        searchViewArch: `
            <search>
                <filter name="filter_1" string="Filter 1" domain="[['foo', '=', 'a']]"/>
                <filter name="filter_2" string="Filter 2" domain="[['foo', '=', 'b']]"/>
            </search>
        `,
        context: {
            search_default_filter_1: true,
        },
    });
    const items = model.getSearchItems((i) => i.isActive);
    expect(items).toHaveLength(1);
    expect(items[0].name).toBe("filter_1");
});
