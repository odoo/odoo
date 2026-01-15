import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, queryFirst, queryOne, queryText, resize } from "@odoo/hoot-dom";
import { animationFrame, Deferred, mockDate } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";
import {
    contains,
    defineModels,
    editFavoriteName,
    fields,
    findComponent,
    getDropdownMenu,
    getFacetTexts,
    getMockEnv,
    getService,
    MockServer,
    mockService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    saveFavorite,
    toggleMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { download } from "@web/core/network/download";
import { PivotController } from "@web/views/pivot/pivot_controller";
import { WebClient } from "@web/webclient/webclient";

function getCurrentValues() {
    return queryAllTexts(".o_pivot_cell_value div").join();
}

async function removeFacet() {
    await contains("div.o_searchview_facet:eq(0) .o_facet_remove").click();
}

async function toggleMultiCurrencyPopover(el) {
    if (getMockEnv().isSmall) {
        await contains(el).click();
    } else {
        await contains(el).hover();
    }
}

class Partner extends models.Model {
    _name = "partner";

    foo = fields.Integer({ groupable: false });
    bar = fields.Boolean({ string: "bar" });
    date = fields.Date();
    product_id = fields.Many2one({ relation: "product" });
    other_product_id = fields.Many2one({ relation: "product" });
    non_stored_m2o = fields.Many2one({ relation: "product", groupable: false });
    customer = fields.Many2one({ relation: "customer" });
    computed_field = fields.Integer({
        string: "Computed and not stored",
        compute: () => 1,
        aggregator: "sum",
        groupable: false,
    });
    company_type = fields.Selection({
        selection: [
            ["company", "Company"],
            ["individual", "individual"],
        ],
    });
    price_nonaggregable = fields.Monetary({
        string: "Price non-aggregable",
        aggregator: undefined,
        currency_field: "currency_id",
        groupable: false,
    });
    reference = fields.Reference({
        string: "Reference",
        selection: [
            ["product", "Product"],
            ["customer", "Customer"],
        ],
        aggregator: "count_distinct",
    });
    parent_id = fields.Many2one({ relation: "partner", groupable: false });
    properties = fields.Properties({
        definition_record: "parent_id",
        definition_record_field: "properties_definition",
    });
    properties_definition = fields.PropertiesDefinition({ string: "Properties", groupable: false });

    display_name = fields.Char({ groupable: false });
    create_date = fields.Datetime({ groupable: false });
    write_date = fields.Datetime({ groupable: false });

    _records = [
        {
            id: 1,
            foo: 12,
            bar: true,
            display_name: "Raoul",
            date: "2016-12-14",
            product_id: 37,
            customer: 1,
            company_type: "company",
            reference: "product,37",
            properties_definition: [
                {
                    name: "my_char",
                    string: "My Char",
                    type: "char",
                },
            ],
        },
        {
            id: 2,
            foo: 1,
            bar: true,
            display_name: "Steven",
            date: "2016-10-26",
            product_id: 41,
            customer: 2,
            company_type: "individual",
            reference: "product,41",
            parent_id: 1,
            properties: {
                my_char: "aaa",
            },
        },
        {
            id: 3,
            foo: 17,
            bar: true,
            display_name: "Taylor",
            date: "2016-12-15",
            product_id: 41,
            customer: 2,
            company_type: "company",
            reference: "customer,1",
            parent_id: 1,
            properties: {
                my_char: "bbb",
            },
        },
        {
            id: 4,
            foo: 2,
            bar: false,
            display_name: "Zara",
            date: "2016-04-11",
            product_id: 41,
            customer: 1,
            company_type: "individual",
            reference: "customer,2",
        },
    ];
}

class Product extends models.Model {
    _name = "product";
    name = fields.Char({ string: "Product Name" });
    _records = [
        {
            id: 37,
            name: "xphone",
        },
        {
            id: 41,
            name: "xpad",
        },
    ];
}

class Currency extends models.Model {
    _name = "res.currency";

    name = fields.Char();
    symbol = fields.Char();
    position = fields.Selection({
        selection: [
            ["after", "A"],
            ["before", "B"],
        ],
    });
    inverse_rate = fields.Float();

    _records = [
        { id: 1, name: "USD", symbol: "$", position: "before", inverse_rate: 1 },
        { id: 2, name: "EUR", symbol: "€", position: "after", inverse_rate: 0.5 },
    ];
}

class Customer extends models.Model {
    _name = "customer";
    name = fields.Char({ string: "Customer Name" });
    _records = [
        {
            id: 1,
            name: "First",
        },
        {
            id: 2,
            name: "Second",
        },
    ];
}

class User extends models.Model {
    _name = "res.users";

    name = fields.Char();

    has_group() {
        return true;
    }
}

defineModels([Partner, Product, Customer, Currency, User]);

test('pivot view without "string" attribute', async () => {
    const view = await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    const model = findComponent(view, (c) => c instanceof PivotController).model;
    // this is important for export functionality.
    expect(model.metaData.title.toString()).toBe("Untitled");
});

test('pivot view with "class" attribute', async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot class="foobar-class"/>`,
    });
    expect(".o_pivot_view").toHaveClass("foobar-class");
});

test("simple pivot rendering", async () => {
    expect.assertions(3);

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="foo" type="measure"/>
			</pivot>
		`,
    });

    expect(".o_pivot_view").toHaveClass("o_view_controller");
    expect("table").toHaveClass("o_enable_linking");
    expect("td.o_pivot_cell_value:contains(32)").toHaveCount(1);
});

test("all measures should be displayed with a pivot_measures context", async () => {
    Partner._fields.bouh = fields.Integer({ string: "bouh", aggregator: "sum" });

    await mountView({
        type: "pivot",
        resModel: "partner",
        context: { pivot_measures: ["foo"] },
        arch: `
			<pivot string="Partners">
				<field name="foo" type="measure"/>
				<field name="bouh" type="measure"/>
			</pivot>
			`,
    });

    await contains("button:contains(Measures)").click();
    expect(".o-dropdown--menu.o-dropdown--menu.dropdown-menu").toHaveCount(1);
    const measures = queryAllTexts(".o-dropdown-item");
    expect(measures).toEqual(["bouh", "Computed and not stored", "Foo", "Count"]);
});

test("pivot rendering with widget", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="foo" type="measure" widget="float_time"/>
			</pivot>
		`,
    });
    expect("td.o_pivot_cell_value:contains(32:00)").toHaveCount(1);
});

test("pivot rendering with widget and options", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
                <field name="foo" type="measure" widget="float_time" options="{'displaySeconds': True}"/>
			</pivot>
		`,
    });
    expect("td.o_pivot_cell_value:contains(32:00:00)").toHaveCount(1);
});

test("pivot rendering with widget and options from model field", async () => {
    Partner._fields.biz = fields.Float({ digits: [16, 2] });
    Partner._records[0].biz = 0.3333333;
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
                <field name="biz" type="measure" widget="percentage"/>
			</pivot>
		`,
    });
    expect("td.o_pivot_cell_value:contains(33.33%)").toHaveCount(1);
});

test("pivot rendering with widget and options from field attrs", async () => {
    Partner._fields.biz = fields.Float({ digits: [16, 2] });
    Partner._records[0].biz = 0.3333333;
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
                <field name="biz" type="measure" widget="float" digits="[16,4]"/>
			</pivot>
		`,
    });
    expect("td.o_pivot_cell_value:contains(0.3333)").toHaveCount(1);
});

test("pivot rendering with string attribute on field", async () => {
    Partner._fields.foo = fields.Integer();

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="foo" string="BAR" type="measure"/>
			</pivot>
		`,
    });

    const toggler = ".o_pivot_buttons button.dropdown-toggle";
    await contains(toggler).click();
    expect(".o-dropdown-item:first").toHaveText("BAR");
    expect(".o_pivot_measure_row").toHaveText("BAR");
});

test("Pivot with integer row group by with 0 as header", async () => {
    Partner._records[0].foo = 0;
    Partner._records[1].foo = 0;
    Partner._records[2].foo = 0;
    Partner._records[3].foo = 0;

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="foo" type="measure"/>
				<field name="foo" type="row"/>
			</pivot>
		`,
    });
    expect(".o_pivot table tr td.o_pivot_cell_value").toHaveCount(2);
    expect(".o_pivot table tbody tr:eq(0) th:eq(0)").toHaveText("Total");
    expect(".o_pivot table tbody tr:eq(0) td:eq(0)").toHaveText("0");
});

test("pivot groupby id shows label, not empty cell", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
            <pivot>
                <field name="id" type="row"/>
                <field name="foo" type="measure"/>
            </pivot>`,
    });

    const rows = queryAllTexts("tbody th");
    expect(rows).toEqual(["Total", "Raoul", "Steven", "Taylor", "Zara"]);
    expect(".o_pivot_cell_value").toHaveCount(5);
});

test("Pivot with integer col group by with 0 as header", async () => {
    Partner._records[0].foo = 0;
    Partner._records[1].foo = 0;
    Partner._records[2].foo = 0;
    Partner._records[3].foo = 0;
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="foo" type="measure"/>
				<field name="foo" type="col"/>
			</pivot>`,
    });
    expect(".o_pivot table thead tr:eq(1) th").toHaveText("0");
});

test("pivot rendering with string attribute on non stored field", async () => {
    Partner._fields.fubar = fields.Integer({
        aggregator: "sum",
        store: false,
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="fubar" string="fubar" type="measure"/>
			</pivot>
		`,
    });
    expect(".o_pivot table thead tr:eq(1) th").toHaveText("fubar");
});

test("pivot rendering with invisible attribute on field", async () => {
    // when invisible, a field should neither be an active measure nor be a selectable measure
    Partner._fields.foo = fields.Integer();
    Partner._fields.foo2 = fields.Integer();
    Partner._fields.computed_field = fields.Integer({
        string: "Computed and not stored",
        compute: () => 1,
        aggregator: null,
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="foo" type="measure"/>
				<field name="foo2" type="measure" invisible="1"/>
			</pivot>
		`,
    });

    // there should be only one displayed measure as the other one is invisible
    expect(".o_pivot_measure_row").toHaveCount(1);
    await contains(".o_pivot_buttons button.dropdown-toggle").click();
    // there should be only one measure besides count, as the other one is invisible
    expect(".dropdown-item").toHaveCount(2);
    expect(".dropdown-item:first").toHaveText("Foo");
    // the invisible field souldn't be in the groupable fields neither
    await contains(".o_pivot_header_cell_closed").click();
    expect('.o-dropdown--menu a[data-field="foo2"]').toHaveCount(0);
});

test("group headers should have a tooltip", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="col"/>
				<field name="date" type="row"/>
			</pivot>
		`,
    });

    expect(queryAll("tbody .o_pivot_header_cell_closed").at(0).dataset.tooltip).toBe("Date");
    expect(queryAll("thead .o_pivot_header_cell_closed").at(1).dataset.tooltip).toBe("Product");
});

test("pivot view add computed fields explicitly defined as measure", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="computed_field" type="measure"/>
			</pivot>`,
    });

    await contains(".o_pivot_buttons button.dropdown-toggle").click();
    expect(".dropdown-item:contains(Computed and not stored)").toHaveCount(1);
    expect(".o_pivot_measure_row").toHaveText("Computed and not stored");
});

test("pivot view do not add number field without aggregator", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="price_nonaggregable"/>
			</pivot>`,
    });
    await contains(".o_pivot_buttons button.dropdown-toggle").click();
    expect(".dropdown-item:contains(Price non-aggregable)").toHaveCount(0);
});

test("clicking on a cell triggers a doAction", async () => {
    expect.assertions(2);
    Partner._views["form,2"] = `<form/>`;
    Partner._views["kanban,5"] = `<kanban/>`;

    mockService("action", {
        doAction(action) {
            expect(action).toEqual({
                context: {
                    lang: "en",
                    tz: "taht",
                    someKey: true,
                    uid: 7,
                    allowed_company_ids: [1],
                },
                domain: [["product_id", "=", 37]],
                name: "Partners",
                res_model: "partner",
                target: "current",
                type: "ir.actions.act_window",
                view_mode: "list",
                views: [
                    [false, "list"],
                    [2, "form"],
                ],
            });
            return Promise.resolve(true);
        },
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="product_id" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
        context: { someKey: true, search_default_test: 3 },
        config: {
            views: [
                [2, "form"],
                [5, "kanban"],
                [false, "list"],
                [false, "pivot"],
            ],
        },
    });

    expect("table").toHaveClass("o_enable_linking");
    await contains(".o_pivot_cell_value:eq(1)").click(); // should trigger a do_action
});

test.tags("desktop");
test("row and column are highlighted when hovering a cell", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="foo" type="col"/>
				<field name="product_id" type="row"/>
			</pivot>`,
    });

    // check row highlighting
    expect("table").toHaveClass("table-hover");

    // check column highlighting
    // hover third measure
    await contains("th.o_pivot_measure_row:nth-of-type(3)").hover();
    expect(".o_cell_hover").toHaveCount(3);
    expect(`tbody tr td:nth-of-type(3)`).toHaveCount(3);
    expect(`tbody tr td:nth-of-type(3)`).toHaveClass("o_cell_hover");
    await contains(".o_pivot_buttons button.dropdown-toggle").hover();
    expect(".o_cell_hover").toHaveCount(0);

    // hover second cell, second row
    await contains("tbody tr:nth-of-type(1) td:nth-of-type(2)").hover();
    expect(".o_cell_hover").toHaveCount(3);
    expect(`tbody tr td:nth-of-type(2)`).toHaveCount(3);
    expect(`tbody tr td:nth-of-type(2)`).toHaveClass("o_cell_hover");
    await contains(".o_pivot_buttons button.dropdown-toggle").hover();
    expect(".o_cell_hover").toHaveCount(0);
});

test('pivot view with disable_linking="True"', async () => {
    mockService("action", {
        doAction() {
            throw new Error("should not execute an action");
        },
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot disable_linking="True">
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    expect("table").not.toHaveClass("o_enable_linking");
    expect(".o_pivot_cell_value").toHaveCount(1);
    expect(".o_pivot_cell_value").not.toHaveClass("cursor-pointer");
    await contains(".o_pivot_cell_value").click(); // should not trigger a do_action
});

test('clicking on the "Total" cell with time range activated', async () => {
    expect.assertions(2);

    mockDate("2016-12-20T1:00:00");

    mockService("action", {
        doAction(action) {
            expect(action.domain).toEqual([
                "&",
                ["date", ">=", "2016-12-01"],
                ["date", "<=", "2016-12-31"],
            ]);
            return Promise.resolve(true);
        },
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot/>",
        searchViewArch: `
			<search>
				<filter name="date_filter" date="date" domain="[]" default_period='month'/>
			</search>`,
        context: { search_default_date_filter: true },
    });

    expect("table").toHaveClass("o_enable_linking");
    await contains(".o_pivot_cell_value").click();
});

test("pivot view grouped by date field", async () => {
    expect.assertions(1);

    onRpc("formatted_read_grouping_sets", ({ kwargs }) => {
        expect(kwargs.aggregates).toEqual(["foo:sum", "__count"]);
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="date" interval="month" type="col"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });
});

test("without measures, pivot view uses __count by default", async () => {
    Partner._fields.computed_field = fields.Integer({
        string: "Computed and not stored",
        aggregator: null,
    });
    Partner._fields.foo = fields.Integer({ aggregator: null });
    expect.assertions(4);

    onRpc("formatted_read_grouping_sets", ({ kwargs }) => {
        expect(kwargs.aggregates).toEqual(["__count"]);
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot></pivot>",
    });

    await contains(".o_pivot_buttons .dropdown-toggle").click();
    const dropdownMenu = getDropdownMenu(".o_pivot_buttons button.dropdown-toggle");
    expect(queryAll(".dropdown-item", { root: dropdownMenu })).toHaveCount(1);
    const measure = dropdownMenu.querySelector(".dropdown-item");
    expect(measure).toHaveText("Count");
    expect(measure).toHaveClass("selected");
});

test("pivot view grouped by many2one field", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    expect(".o_pivot_header_cell_opened").toHaveCount(1);
    expect(".o_pivot_header_cell_closed:contains(xphone)").toHaveCount(1);
    expect(".o_pivot_header_cell_closed:contains(xpad)").toHaveCount(1);
});

test("pivot view can be reloaded", async () => {
    let readGroupCount = 0;
    onRpc("formatted_read_grouping_sets", () => {
        readGroupCount++;
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot></pivot>",
        searchViewArch: `
			<search>
				<filter name="some_filter" string="Some Filter" domain="[('foo', '>', 10)]"/>
			</search>`,
    });
    expect("td.o_pivot_cell_value:contains(4)").toHaveCount(1);
    expect(readGroupCount).toBe(1);
    await toggleSearchBarMenu();
    await toggleMenuItem("Some Filter");
    expect("td.o_pivot_cell_value:contains(2)").toHaveCount(1);
    expect(readGroupCount).toBe(2);
});

test.tags("desktop");
test("basic folding/unfolding", async () => {
    let rpcCount = 0;
    onRpc("formatted_read_grouping_sets", () => {
        rpcCount++;
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    expect("tbody tr").toHaveCount(3);
    // click on the opened header to close it
    await contains(".o_pivot_header_cell_opened").click();
    expect("tbody tr").toHaveCount(1);
    // click on closed header to open dropdown
    await contains("tbody .o_pivot_header_cell_closed").click();
    expect(".o-dropdown--menu").toHaveCount(1);
    expect(queryAllTexts(".o-dropdown--menu .o-dropdown-item")).toEqual([
        "Company type",
        "Customer",
        "Date",
        "Other product",
        "Product",
        "bar",
    ]);
    // open the Date sub dropdown
    await contains(".o-dropdown--menu .dropdown-toggle.o_menu_item").hover();
    const subDropdownMenu = getDropdownMenu(".o-dropdown--menu .dropdown-toggle.o_menu_item");
    expect(subDropdownMenu).toHaveText("Year\nQuarter\nMonth\nWeek\nDay");

    await contains(queryOne(".dropdown-item:eq(2)", { root: subDropdownMenu })).click();
    expect("tbody tr").toHaveCount(4);
    expect(rpcCount).toBe(2);
});

test.tags("desktop");
test("more folding/unfolding", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    // open dropdown to zoom into first row
    await contains("tbody .o_pivot_header_cell_closed").click();
    // click on date by day
    await contains(".o-dropdown--menu .dropdown-toggle").hover();
    const subDropdownMenu = getDropdownMenu(".o-dropdown--menu .dropdown-toggle");
    await contains(queryOne("span:nth-child(5)", { root: subDropdownMenu })).click();

    // open dropdown to zoom into second row
    await contains("tbody th.o_pivot_header_cell_closed:eq(1)").click();
    expect("tbody tr").toHaveCount(7);
});

test("fold and unfold header group", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="col"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    expect("thead tr").toHaveCount(3);

    // fold opened col group
    await contains("thead .o_pivot_header_cell_opened").click();
    expect("thead tr").toHaveCount(2);

    // unfold it
    await contains("thead .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu span:nth-child(5)").click();
    expect("thead tr").toHaveCount(3);
});

test("unfold second header group", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="col"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    expect("thead tr").toHaveCount(3);
    let values = ["12", "20", "32"];
    expect(getCurrentValues()).toBe(values.join(","));

    // unfold it
    await contains("thead .o_pivot_header_cell_closed:last-child").click();
    await contains(".o-dropdown--menu span:nth-child(1)").click();
    expect("thead tr").toHaveCount(4);
    values = ["12", "17", "3", "32"];
    expect(getCurrentValues()).toBe(values.join(","));
});

test("pivot renders group dropdown same as search groupby dropdown if group bys are specified in search arch", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
				<field name="bar" type="col"/>
				<field name="foo" type="measure"/>
			</pivot>`,
        // TOASK DAM: <search><field/></search> won´t appear in groupbymenu ?
        searchViewArch: `
			<search>
				<filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
				<filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
				<filter name="product_id" string="product" context="{'group_by': 'product_id'}"/>
			</search>`,
    });

    // open group by dropdown
    await toggleSearchBarMenu();
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(6);
    expect(".o-dropdown--menu .o_add_custom_group_menu").toHaveCount(1);
    // click on closed header to open dropdown
    await contains("tbody tr:last-child .o_pivot_header_cell_closed").click();
    expect(".dropdown-menu > .dropdown-item").toHaveCount(4);
    expect(".o-dropdown--menu .o_add_custom_group_menu").toHaveCount(1);
    // check custom groupby selection has groupable fields only
    expect(".o_add_custom_group_menu option:not([disabled])").toHaveCount(6);
    const optionDescriptions = queryAllTexts(".o_add_custom_group_menu option:not([disabled])");
    expect(optionDescriptions).toEqual([
        "Company type",
        "Customer",
        "Date",
        "Other product",
        "Product",
        "bar",
    ]);
});

test("headers group dropdown should close on selection", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
            <pivot>
                <field name="product_id" type="row"/>
                <field name="foo" type="measure"/>
            </pivot>`,
    });
    // 1. with first-level dropdown groupby
    // open a header group dropdown
    await contains("tbody tr .o_pivot_header_cell_closed").click();
    expect(".o-dropdown--menu").toHaveCount(1);
    // select an item
    await contains(".o-dropdown-item").click();
    expect(".o-dropdown--menu").toHaveCount(0);

    // 2. with sub dropdown groupby
    // open a header group dropdown
    await contains("tbody tr .o_pivot_header_cell_closed").click();
    expect(".o-dropdown--menu").toHaveCount(1);
    // open a subdropdown
    await contains(".o-dropdown--menu .dropdown-toggle").click();
    expect(".o-dropdown--menu").toHaveCount(2);
    // select an item
    const subDropdownMenu = getDropdownMenu(".o-dropdown--menu .dropdown-toggle");
    await contains(queryFirst(".o-dropdown-item", { root: subDropdownMenu })).click();
    expect(".o-dropdown--menu").toHaveCount(0);

    // 3. with custom groupby
    // open a header group dropdown
    await contains("tbody tr .o_pivot_header_cell_closed").click();
    expect(".o-dropdown--menu").toHaveCount(1);
    await contains(`.o_add_custom_group_menu`).select("date");
    expect(".o-dropdown--menu").toHaveCount(0);
});

test("pivot group dropdown sync with search groupby dropdown", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
				<filter name="product_id" string="product" context="{'group_by': 'product_id'}"/>
			</search>`,
    });

    // open group by dropdown
    await toggleSearchBarMenu();
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(5);
    // click on closed header to open dropdown
    await contains("tbody tr:last-child .o_pivot_header_cell_closed").click();
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(3);
    // add a custom group in searchview groupby
    await toggleSearchBarMenu();
    await contains(`.o_add_custom_group_menu`).select("company_type");
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(6);
    await contains("tbody tr:last-child .o_pivot_header_cell_closed").click();
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(3);
    // add a custom group in pivot groupby
    await contains(`.o_add_custom_group_menu`).select("date");
    // click on closed header to open groupby selection dropdown
    await contains("tbody tr:last-child .o_pivot_header_cell_closed").click();
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(4);
    // applying custom groupby in pivot groupby dropdown will not update search dropdown
    await toggleSearchBarMenu();
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(6);
});

test("pivot custom groupby: grouping on date field use default interval month", async () => {
    expect.assertions(1);

    let checkReadGroup = false;
    onRpc("formatted_read_grouping_sets", ({ kwargs }) => {
        if (checkReadGroup) {
            expect(kwargs.grouping_sets[0]).toEqual(["date:month"]);
            checkReadGroup = false;
        }
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot>
					<field name="product_id" type="row"/>
					<field name="foo" type="measure"/>
				</pivot>`,
        searchViewArch: `
				<search>
					<filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
				</search>`,
    });

    // click on closed header to open dropdown and apply groupby on date field
    await contains("thead .o_pivot_header_cell_closed").click();
    checkReadGroup = true;
    await contains(`.o_add_custom_group_menu`).select("date");
});

test("pivot groupby dropdown renders custom search at the end with separator", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot>
					<field name="product_id" type="row"/>
					<field name="foo" type="measure"/>
				</pivot>`,
        searchViewArch: `
				<search>
					<filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
					<filter name="product_id" string="product" context="{'group_by': 'product_id'}"/>
				</search>`,
    });

    // open group by dropdown
    await toggleSearchBarMenu();
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(5);
    await contains(`.o_add_custom_group_menu`).select("company_type");
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(6);
    // click on closed header to open dropdown
    await contains("tbody .o_pivot_header_cell_closed:eq(1)").click();
    let items = queryAll(".o_menu_item:not(select)");
    expect(queryAllTexts(items)).toEqual(["bar", "product"]);
    expect(".o-dropdown--menu .dropdown-divider").toHaveCount(1);
    expect(items[items.length - 1].nextElementSibling).toHaveClass("dropdown-divider");
    // add a custom group in pivot groupby
    await contains(`.o_add_custom_group_menu`).select("customer");
    await contains("tbody .o_pivot_header_cell_closed:eq(1)").click();
    items = queryAll(".o_menu_item:not(select)");
    expect(queryAllTexts(items)).toEqual(["bar", "product", "Customer"]);
    expect(".o-dropdown--menu .dropdown-divider").toHaveCount(2);
    expect(items[items.length - 1].previousElementSibling).toHaveClass("dropdown-divider");
    expect(items[items.length - 1].nextElementSibling).toHaveClass("dropdown-divider");
});

test("pivot view without group by specified in search arch", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    // open group by dropdown
    await toggleSearchBarMenu();
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(3);
    expect(".o-dropdown--menu .o_add_custom_group_menu").toHaveCount(1);
    // click on closed header to open dropdown
    await contains("tbody .o_pivot_header_cell_closed:eq(1)").click();
    expect(".o-dropdown--menu .o_menu_item").toHaveCount(7);
    expect(".o-dropdown--menu .o_add_custom_group_menu").toHaveCount(1);
});

test("pivot view do not show custom group selection if there are no groupable fields", async () => {
    for (const fieldName of ["bar", "company_type", "customer", "date", "other_product_id"]) {
        delete Partner._fields[fieldName];
    }

    // Keep product_id but make it ungroupable
    Partner._fields.product_id = fields.Many2one({
        relation: "product",
        groupable: false,
    });

    Partner._records = [
        {
            id: 1,
            foo: 12,
            product_id: 37,
        },
    ];

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot>
					<field name="foo" type="measure"/>
					<field name="product_id" invisible="1"/>
				</pivot>`,
        searchViewArch: `
				<search>
					<filter name="product_id" string="product" context="{'group_by': 'product_id'}"/>
				</search>`,
    });

    // open group by dropdown
    await toggleSearchBarMenu();
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(3);
    expect(".o-dropdown--menu .o_add_custom_group_menu").toHaveCount(0);

    // click on closed header to open dropdown
    await contains("tbody .o_pivot_header_cell_closed").click();
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(1);
    expect(".o-dropdown--menu .o_add_custom_group_menu").toHaveCount(0);
});

test("can toggle extra measure", async () => {
    let rpcCount = 0;
    onRpc(() => {
        rpcCount++;
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    rpcCount = 0;
    expect(".o_pivot_cell_value").toHaveCount(3);
    await contains(".o_pivot_buttons button.dropdown-toggle").click();
    expect(".dropdown-item:contains(Count)").not.toHaveClass("selected");
    await contains(".dropdown-item:contains(Count):eq(0").click();
    expect(".dropdown-item:contains(Count)").toHaveClass("selected");
    expect(".o_pivot_cell_value").toHaveCount(6);
    expect(rpcCount).toBe(1);
    await contains(".dropdown-item:contains(Count):eq(0)").click();
    expect(".dropdown-item:contains(Count):eq(0)").not.toHaveClass("selected");
    expect(".o_pivot_cell_value").toHaveCount(3);
    expect(rpcCount).toBe(1);
});

test("no content helper when no active measure", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot/>`,
    });

    expect(".o_view_nocontent").toHaveCount(0);
    expect("table").toHaveCount(1);

    await contains(".o_pivot_buttons button.dropdown-toggle").click();
    await contains(".dropdown-item:contains(Count):eq(0)").click();

    expect(".o_view_nocontent").toHaveCount(1);
    expect("table").toHaveCount(0);
});

test("no content helper when no data", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot/>`,
        searchViewArch: `
			<search>
				<filter name="some_filter" string="Some Filter" domain="[('foo', '=', 12345)]"/>
			</search>`,
    });

    expect(".o_view_nocontent").toHaveCount(0);
    expect("table").toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("Some Filter");

    expect(".o_view_nocontent").toHaveCount(1);
    expect("table").toHaveCount(0);
});

test("no content helper when no data, part 2", async () => {
    Partner._records = [];

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot/>",
    });

    expect(".o_view_nocontent").toHaveCount(1);
});

test.tags("desktop");
test("no content helper when no data, part 3", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot/>",
        searchViewArch: `
			<search>
				<field name="foo"/>
				<filter name="some_filter" string="Some Filter" domain="[('foo', '>', 10)]"/>
			</search>`,
        context: {
            search_default_foo: 12345,
        },
    });

    expect(".o_searchview .o_searchview_facet").toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("Some Filter");
    expect(".o_searchview .o_searchview_facet").toHaveCount(2);
    expect(".o_view_nocontent").toHaveCount(1);

    await toggleMenuItem("Some Filter");
    expect(".o_searchview .o_searchview_facet").toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(1);

    await contains(".o_facet_remove").click();
    expect(".o_searchview .o_searchview_facet").toHaveCount(0);
    expect(".o_view_nocontent").toHaveCount(0);

    // tries to open a field selection menu, to make sure it was not
    // removed from the dom.
    await contains("tbody .o_pivot_header_cell_closed").click();
    expect(".o-dropdown--menu").toHaveCount(1);
});

test("tries to restore previous state after domain change", async () => {
    let rpcCount = 0;
    onRpc(() => {
        rpcCount++;
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter name="my_filter" string="My Filter" domain="[('foo', '=', 12345)]"/>
			</search>`,
    });

    expect(".o_pivot_cell_value").toHaveCount(3);
    expect(".o_pivot_measure_row:contains(Foo)").toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect("table").toHaveCount(0);

    rpcCount = 0;
    await removeFacet();

    expect("table").toHaveCount(1);
    expect(rpcCount).toBe(1);
    expect(".o_pivot_cell_value").toHaveCount(3);
    expect(".o_pivot_measure_row:contains(Foo)").toHaveCount(1);
});

test("can be grouped with the search view", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter string="Product" name="product_id" context="{'group_by':'product_id'}"/>
			</search>`,
    });

    expect(".o_pivot_cell_value").toHaveCount(1);
    expect("tbody tr").toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("Product");

    expect(".o_pivot_cell_value").toHaveCount(3);
    expect("tbody tr").toHaveCount(3);
});

test("can sort data in a column by clicking on header", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
				<field name="product_id" type="row"/>
			</pivot>`,
    });

    let values = ["32", "12", "20"];
    expect(getCurrentValues()).toBe(values.join(","));

    await contains("th.o_pivot_measure_row").click();

    values = ["32", "12", "20"];
    expect(getCurrentValues()).toBe(values.join(","));

    await contains("th.o_pivot_measure_row").click();

    values = ["32", "20", "12"];
    expect(getCurrentValues()).toBe(values.join(","));
});

test("can expand all rows", async () => {
    let nbReadGroups = 0;
    onRpc("formatted_read_grouping_sets", () => {
        nbReadGroups++;
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
				<field name="product_id" type="row"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter string="Date" name="date" context="{'group_by':'date'}"/>
				<filter string="Product" name="product_id" context="{'group_by':'product_id'}"/>
			</search>`,
    });

    expect(nbReadGroups).toBe(1);
    expect(getCurrentValues()).toBe("32,12,20");

    // expand on date:days, product
    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    await toggleMenuItemOption("Date", "Month");
    nbReadGroups = 0;
    await toggleMenuItem("Product");

    expect(nbReadGroups).toBe(1);
    expect("tbody tr").toHaveCount(8);

    // collapse the first two rows
    await contains("tbody .o_pivot_header_cell_opened:eq(2)").click();
    await contains("tbody .o_pivot_header_cell_opened:eq(1)").click();

    expect("tbody tr").toHaveCount(6);

    // expand all
    nbReadGroups = 0;
    await contains(".o_pivot_expand_button").click();

    expect(nbReadGroups).toBe(1);
    expect("tbody tr").toHaveCount(8);
});

test("expand all with a delay", async () => {
    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
				<field name="product_id" type="row"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter string="Date" name="date" context="{'group_by':'date'}"/>
				<filter string="Product" name="product_id" context="{'group_by':'product_id'}"/>
			</search>`,
    });

    // expand on date:days, product
    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    await toggleMenuItemOption("Date", "Month");
    await toggleMenuItem("Product");
    expect("tbody tr").toHaveCount(8);

    // collapse the first two rows
    await contains("tbody .o_pivot_header_cell_opened:eq(2)").click();
    await contains("tbody .o_pivot_header_cell_opened:eq(1)").click();

    expect("tbody tr").toHaveCount(6);

    // expand all
    def = new Deferred();
    await contains(".o_pivot_expand_button").click();
    expect("tbody tr").toHaveCount(6);
    def.resolve();
    await animationFrame();
    expect("tbody tr").toHaveCount(8);
});

test("can download a file", async () => {
    expect.assertions(1);

    patchWithCleanup(download, {
        _download: (options) => {
            expect(options.url).toBe("/web/pivot/export_xlsx");
            return Promise.resolve();
        },
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="date" interval="month" type="col"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    await contains(".o_pivot_download").click();
});

test("download a file with single measure, measure row displayed in table", async () => {
    expect.assertions(2);

    const downloadDef = new Deferred();
    patchWithCleanup(download, {
        _download: async ({ url, data }) => {
            data = JSON.parse(await data.data.text());
            expect(url).toBe("/web/pivot/export_xlsx");
            expect(data.measure_headers.length).toBe(4);
            downloadDef.resolve();
            return Promise.resolve();
        },
    });

    await mountView({
        type: "pivot",
        resModel: "partner",

        arch: `
				<pivot>
					<field name="date" interval="month" type="col"/>
					<field name="foo" type="measure"/>
				</pivot>`,
    });

    await contains(".o_pivot_download").click();
    await downloadDef;
});

test("download button is disabled when there is no data", async () => {
    Partner._records = [];

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="date" interval="month" type="col"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    expect(".o_pivot_download").not.toBeEnabled();
});

test("correctly save measures and groupbys to favorite", async () => {
    expect.assertions(3);

    let expectedContext;
    onRpc("create_filter", ({ args }) => {
        expect(args[0].context).toEqual(expectedContext);
        return true;
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="date" interval="day" type="col"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    expectedContext = {
        group_by: [],
        pivot_column_groupby: ["date:day"],
        pivot_measures: ["foo"],
        pivot_row_groupby: [],
    };
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("Fav1");
    await saveFavorite();

    // expand header on field customer
    await contains("thead .o_pivot_header_cell_closed:eq(1)").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(1)").click();
    expectedContext = {
        group_by: [],
        pivot_column_groupby: ["date:day", "customer"],
        pivot_measures: ["foo"],
        pivot_row_groupby: [],
    };
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("Fav2");
    await saveFavorite();

    // expand row on field product_id
    await contains("tbody .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(4)").click();
    expectedContext = {
        group_by: [],
        pivot_column_groupby: ["date:day", "customer"],
        pivot_measures: ["foo"],
        pivot_row_groupby: ["product_id"],
    };
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("Fav3");
    await saveFavorite();
});

test.tags("desktop");
test("correctly remove pivot_ keys from the context", async () => {
    expect.assertions(5);

    // in this test, we use "foo" as a measure
    Partner._fields.foo = fields.Integer({
        groupable: false,
    });
    Partner._fields.amount = fields.Float();

    let expectedContext;

    onRpc("create_filter", ({ args }) => {
        expect(args[0].context).toEqual(expectedContext);
        return true;
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="date" interval="day" type="col"/>
				<field name="amount" type="measure"/>
			</pivot>`,
        context: {
            search_default_initial_context: 1,
        },
        searchViewArch: `
			<search>
				<filter
					name="initial_context"
					string="Initial favorite"
					domain="[]"
					context="{
						'pivot_measures': ['foo'],
						'pivot_column_groupby': ['customer'],
						'pivot_row_groupby': ['product_id'],
					}"
				/>
			</search>`,
    });

    // Unload the filter
    await removeFacet(); // remove previous favorite
    expectedContext = {
        group_by: [],
        pivot_column_groupby: ["customer"],
        pivot_measures: ["foo"],
        pivot_row_groupby: ["product_id"],
    };
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("1");
    await saveFavorite();

    // Let's get rid of the rows groupBy
    await contains("tbody .o_pivot_header_cell_opened").click();
    expectedContext = {
        group_by: [],
        pivot_column_groupby: ["customer"],
        pivot_measures: ["foo"],
        pivot_row_groupby: [],
    };
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("2");
    await saveFavorite();

    // And now, get rid of both col and row groupby
    //await contains("tbody .o_pivot_header_cell_opened").click(); //It was already removed
    await contains("thead .o_pivot_header_cell_opened").click();
    expectedContext = {
        group_by: [],
        pivot_column_groupby: [],
        pivot_measures: ["foo"],
        pivot_row_groupby: [],
    };
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("3");
    await saveFavorite();

    // Group row by product_id
    await contains("tbody .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu span:nth-child(5)").click();
    expectedContext = {
        group_by: [],
        pivot_column_groupby: [],
        pivot_measures: ["foo"],
        pivot_row_groupby: ["product_id"],
    };
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("4");
    await saveFavorite();

    // Group column by customer
    await contains("thead .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu span:nth-child(2)").click();
    expectedContext = {
        group_by: [],
        pivot_column_groupby: ["customer"],
        pivot_measures: ["foo"],
        pivot_row_groupby: ["product_id"],
    };
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("5");
    await saveFavorite();
});

test("Apply two groupby, and remove facet", async () => {
    Partner._views["pivot"] = `<pivot>
		<field name="customer" type="row"/>
	</pivot>`;
    Partner._views["search"] = `<search>
		<filter name="group_by_product" string="Product" domain="[]" context="{'group_by': 'product_id'}"/>
		<filter name="group_by_bar" string="Bar" domain="[]" context="{'group_by': 'bar'}"/>
	</search>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });

    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("First");

    // Apply both groupbys
    await toggleSearchBarMenu();
    await toggleMenuItem("Product");
    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("xphone");

    await toggleMenuItem("Bar");
    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("Yes");

    // remove filter
    await removeFacet();

    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("Yes");
});

test("Add a group by on the CP when a favorite already exists", async () => {
    Partner._views["search"] = `<search>
		<filter name="groubybar" string="Bar" domain="[]" context="{'group_by': 'bar'}"/>
	</search>`;

    Partner._filters = [
        {
            context: "{'pivot_row_groupby': ['date']}",
            domain: "[]",
            id: 7,
            is_default: true,
            name: "My favorite",
            sort: "[]",
            user_ids: [2],
        },
    ];

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });

    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("April 2016");

    // Apply BAR groupbys
    await toggleSearchBarMenu();
    await toggleMenuItem("Bar");
    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("No");

    // remove groupBy
    await toggleMenuItem("Bar");
    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("April 2016");

    // remove all facets
    await removeFacet();

    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("April 2016");
});

test("Adding a Favorite at anytime should modify the row/column groupby", async () => {
    Partner._views["pivot"] = `<pivot>
			<field name="customer" type="row"/>
			<field name="date" interval="month" type="col" />
		</pivot>`;
    Partner._filters = [
        {
            user_ids: [2],
            name: "My favorite",
            id: 5,
            context: `{"pivot_row_groupby":["product_id"], "pivot_column_groupby": ["bar"]}`,
            sort: "[]",
            domain: "",
            is_default: false,
            model_id: "partner",
            action_id: false,
        },
    ];

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });

    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("First");

    expect(queryFirst("thead .o_pivot_header_cell_closed")).toHaveText("April 2016");

    // activate the unique existing favorite
    await toggleSearchBarMenu();
    await toggleMenuItem("my favorite");
    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("xphone");

    expect(queryFirst("thead .o_pivot_header_cell_closed")).toHaveText("No");

    // desactivate the unique existing favorite
    await toggleMenuItem("my favorite");

    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("xphone");

    expect(queryFirst("thead .o_pivot_header_cell_closed")).toHaveText("No");

    // Let's get rid of the rows and columns groupBy
    await contains("tbody .o_pivot_header_cell_opened").click();
    await contains("thead .o_pivot_header_cell_opened").click();

    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("Total");

    expect(queryFirst("thead .o_pivot_header_cell_closed")).toHaveText("Total");

    // activate AGAIN the unique existing favorite
    await toggleSearchBarMenu();
    await toggleMenuItem("my favorite");

    expect(queryFirst("tbody .o_pivot_header_cell_closed")).toHaveText("xphone");

    expect(queryFirst("thead .o_pivot_header_cell_closed")).toHaveText("No");
});

test("Unload Filter, reset display, load another filter", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
			</pivot>`,
        context: {
            pivot_measures: ["foo"],
            pivot_column_groupby: ["customer"],
            pivot_row_groupby: ["product_id"],
        },
        searchViewArch: `
			<search>
				<filter
					name="no_context_filter"
					string="My fake favorite"
					domain="[]"
					context="{}"
				/>
				<filter
					name="reset_filter"
					string="My fake favorite 2"
					domain="[]"
					context="{
						'pivot_measures': ['foo'],
						'pivot_column_groupby': ['customer'],
						'pivot_row_groupby': ['product_id'],
					}"
				/>
			</search>`,
    });

    // Check Columns
    expect("thead .o_pivot_header_cell_opened").toHaveCount(1);
    expect('thead tr:contains("First")').toHaveCount(1);
    expect('thead tr:contains("Second")').toHaveCount(1);

    // Check Rows
    expect("tbody .o_pivot_header_cell_opened").toHaveCount(1);
    expect('tbody tr:contains("xphone")').toHaveCount(1);
    expect('tbody tr:contains("xpad")').toHaveCount(1);

    // Equivalent to unload the filter
    await toggleSearchBarMenu();
    await toggleMenuItem("My fake favorite");
    // collapse all headers
    await contains(".o_pivot_header_cell_opened:first-child").click();
    await contains(".o_pivot_header_cell_opened").click();

    // Check Columns
    expect("thead .o_pivot_header_cell_closed").toHaveCount(1);
    expect('thead tr:contains("First")').toHaveCount(0);
    expect('thead tr:contains("Second")').toHaveCount(0);

    // Check Rows
    expect("tbody .o_pivot_header_cell_closed").toHaveCount(1);
    expect('tbody tr:contains("xphone")').toHaveCount(0);
    expect('tbody tr:contains("xpad")').toHaveCount(0);

    // Equivalent to load another filter
    await removeFacet(); // remove previously saved favorite
    await toggleSearchBarMenu();
    await toggleMenuItem("My fake favorite 2");

    // Check Columns
    expect("thead .o_pivot_header_cell_opened").toHaveCount(1);
    expect('thead tr:contains("First")').toHaveCount(1);
    expect('thead tr:contains("Second")').toHaveCount(1);

    // Check Rows
    expect("tbody .o_pivot_header_cell_opened").toHaveCount(1);
    expect('tbody tr:contains("xphone")').toHaveCount(1);
    expect('tbody tr:contains("xpad")').toHaveCount(1);
});

test("Reload, group by columns, reload", async () => {
    expect.assertions(2);

    let expectedContext;

    onRpc("create_filter", ({ args }) => {
        expect(args[0].context).toEqual(expectedContext);
        return true;
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot/>",
        searchViewArch: `
			<search>
				<filter name="my_filter_1" string="My Filter 1" domain="[('product_id', '=', 37)]"/>
				<filter name="my_filter_2" string="My Filter 2" domain="[('product_id', '=', 41)]"/>
			</search>`,
    });

    // Set a column groupby
    await contains("thead .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(1)").click();

    // Set a domain
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter 1");

    // Save to favorites and check that column groupbys were not lost
    expectedContext = {
        group_by: [],
        pivot_column_groupby: ["customer"],
        pivot_measures: ["__count"],
        pivot_row_groupby: [],
    };
    await toggleSaveFavorite();
    await editFavoriteName("My favorite 1");
    await saveFavorite();

    // Set a column groupby
    await removeFacet(); // remove previously saved favorite
    await contains("thead .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(4)").click();

    // Set a domain
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter 2");

    expectedContext = {
        group_by: [],
        pivot_column_groupby: ["customer", "product_id"],
        pivot_measures: ["__count"],
        pivot_row_groupby: [],
    };
    await toggleSaveFavorite();
    await editFavoriteName("My favorite 2");
    await saveFavorite();
});

test("folded groups remain folded at reload", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
				<field name="company_type" type="col"/>
				<field name="foo" type="measure"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter name="dummy_filter" string="Dummy Filter" domain="[('id', '>', 0)]"/>
			</search>`,
    });

    let values = ["29", "3", "32", "12", "12", "17", "3", "20"];
    expect(getCurrentValues()).toBe(values.join(","));

    // expand a col group
    await contains("thead .o_pivot_header_cell_closed:eq(1)").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(1)").click();

    values = ["29", "2", "1", "32", "12", "12", "17", "2", "1", "20"];
    expect(getCurrentValues()).toBe(values.join(","));

    // expand a row group
    await contains("tbody .o_pivot_header_cell_closed:eq(1)").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(3)").click();

    values = ["29", "2", "1", "32", "12", "12", "17", "2", "1", "20", "17", "2", "1", "20"];
    expect(getCurrentValues()).toBe(values.join(","));

    // reload (should keep folded groups folded as col/row groupbys didn't change)
    await toggleSearchBarMenu();
    await toggleMenuItem("Dummy Filter");

    expect(getCurrentValues()).toBe(values.join(","));

    await contains(".o_pivot_expand_button").click();

    // sanity check of what the table should look like if all groups are
    // expanded, to ensure that the former asserts are pertinent
    values = [
        "12",
        "17",
        "2",
        "1",
        "32",
        "12",
        "12",
        "12",
        "12",
        "17",
        "2",
        "1",
        "20",
        "17",
        "2",
        "1",
        "20",
    ];
    expect(getCurrentValues()).toBe(values.join(","));
});

test("Empty results keep groupbys", async () => {
    expect.assertions(6);

    const expectedContext = {
        group_by: [],
        pivot_column_groupby: ["customer"],
        pivot_measures: ["__count"],
        pivot_row_groupby: [],
    };

    onRpc("create_filter", ({ args }) => {
        expect(args[0].context).toEqual(expectedContext);
        return true;
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot/>",
        searchViewArch: `
			<search>
				<filter name="my_filter_1" string="My Filter 1" domain="[('id', '=', 0)]"/>
				<filter name="my_filter_2" string="My Filter 2" domain="[('product_id', '=', 37)]"/>
			</search>`,
    });

    // Set a column groupby
    await contains("thead .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(1)").click();

    expect("table").toHaveCount(1);

    // Set a domain for empty results
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter 1");
    expect("table").toHaveCount(0);

    await toggleSaveFavorite();
    await editFavoriteName("My favorite 1");
    await saveFavorite();

    // Set a domain for not empty results
    await removeFacet(); // remove previously saved favorite
    expect("table").toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter 2");
    expect("table").toHaveCount(1);

    await toggleSaveFavorite();
    await editFavoriteName("My favorite 2");
    await saveFavorite();
});

test("correctly uses pivot_ keys from the context", async () => {
    // in this test, we use "foo" as a measure
    Partner._fields.foo = fields.Integer({
        groupable: false,
    });
    Partner._fields.amount = fields.Float();

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="date" interval="day" type="col"/>
				<field name="amount" type="measure"/>
			</pivot>`,
        context: {
            pivot_measures: ["foo"],
            pivot_column_groupby: ["customer"],
            pivot_row_groupby: ["product_id"],
        },
    });

    expect("thead .o_pivot_header_cell_opened").toHaveCount(1);
    expect("thead .o_pivot_header_cell_closed:contains(First)").toHaveCount(1);
    expect("thead .o_pivot_header_cell_closed:contains(Second)").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_opened").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_closed:contains(xphone)").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_closed:contains(xpad)").toHaveCount(1);
    expect("tbody tr td:eq(2)").toHaveText("32");
});

test.tags("desktop");
test("clear table cells data after closeGroup", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot/>",
        groupBy: ["product_id"],
    });

    await contains("thead .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-toggle").hover();
    await contains(".o-overlay-item:nth-child(2) .o-dropdown--menu .dropdown-item:eq(3)").click();

    // close and reopen row groupings after changing value
    MockServer.env["partner"].find((r) => r.product_id === 37).date = "2016-10-27";

    await contains("tbody .o_pivot_header_cell_opened").click();
    await contains("tbody .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(4)").click();
    expect(".o_pivot_cell_value:eq(4)").toHaveText(""); // xphone December 2016

    // invert axis, and reopen column groupings
    await contains(".o_pivot_buttons .o_pivot_flip_button").click();
    await contains("thead .o_pivot_header_cell_opened").click();
    await contains("thead .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(4)").click();
    expect(".o_pivot_cell_value:eq(3)").toHaveText(""); // December 2016 xphone
});

test("correctly group data after flip (1)", async () => {
    Partner._views[
        "search"
    ] = `<search><filter name="bayou" string="Bayou" domain="[(1,'=',1)]"/></search>`;
    Partner._views["list"] = `<list><field name="foo"/></list>`;
    Partner._views["form"] = `<form><field name="foo"/></form>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
        context: { group_by: ["product_id"] },
    });

    expect(queryAllTexts("tbody th")).toEqual(["Total", "xphone", "xpad"]);
    // flip axis
    await contains(".o_pivot_flip_button").click();
    expect(queryAllTexts("tbody th")).toEqual(["Total"]);
    // select filter "Bayou" in control panel
    await toggleSearchBarMenu();
    await toggleMenuItem("Bayou");
    expect(queryAllTexts("tbody th")).toEqual(["Total", "xphone", "xpad"]);
    // close row header "Total"
    await contains("tbody .o_pivot_header_cell_opened").click();
    expect(queryAllTexts("tbody th")).toEqual(["Total"]);
});

test("correctly group data after flip (2)", async () => {
    Partner._views[
        "search"
    ] = `<search><filter name="bayou" string="Bayou" domain="[(1,'=',1)]"/></search>`;
    Partner._views["list"] = `<list><field name="foo"/></list>`;
    Partner._views["form"] = `<form><field name="foo"/></form>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
        context: { group_by: ["product_id"] },
    });

    expect(queryAllTexts("tbody th")).toEqual(["Total", "xphone", "xpad"]);
    // select filter "Bayou" in control panel
    await toggleSearchBarMenu();
    await toggleMenuItem("Bayou");
    expect(queryAllTexts("tbody th")).toEqual(["Total", "xphone", "xpad"]);
    // flip axis
    await contains(".o_pivot_flip_button").click();
    expect(queryAllTexts("tbody th")).toEqual(["Total"]);
    // unselect filter "Bayou" in control panel
    await toggleSearchBarMenu();
    await toggleMenuItem("Bayou");
    expect(queryAllTexts("tbody th")).toEqual(["Total", "xphone", "xpad"]);
    // close row header "Total"
    await contains("tbody .o_pivot_header_cell_opened").click();
    expect(queryAllTexts("tbody th")).toEqual(["Total"]);
});

test("correctly uses pivot_ keys from the context (at reload)", async () => {
    // in this test, we use "foo" as a measure
    Partner._fields.foo = fields.Integer({
        groupable: false,
    });
    Partner._fields.amount = fields.Float();

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="date" interval="day" type="col"/>
				<field name="amount" type="measure"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter
					name="filter_with_context"
					string="My fake favorite"
					domain="[]"
					context="{
						'pivot_measures': ['foo'],
						'pivot_column_groupby': ['customer'],
						'pivot_row_groupby': ['product_id']
					}"
				/>
			</search>`,
    });

    expect("tbody tr td.o_pivot_cell_value:eq(4)").toHaveText("0.00");
    await toggleSearchBarMenu();
    await toggleMenuItem("My fake favorite");
    expect("thead .o_pivot_header_cell_opened").toHaveCount(1);
    expect("thead .o_pivot_header_cell_closed:contains(First)").toHaveCount(1);
    expect("thead .o_pivot_header_cell_closed:contains(Second)").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_opened").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_closed:contains(xphone)").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_closed:contains(xpad)").toHaveCount(1);
    expect("tbody tr td:eq(2)").toHaveText("32");
});

test("correctly use group_by key from the context", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="customer" type="col" />
				<field name="foo" type="measure" />
			</pivot>`,
        groupBy: ["product_id"],
    });

    expect("thead .o_pivot_header_cell_opened").toHaveCount(1);
    expect("thead .o_pivot_header_cell_closed:contains(First)").toHaveCount(1);
    expect("thead .o_pivot_header_cell_closed:contains(Second)").toHaveCount(1);

    expect("tbody .o_pivot_header_cell_opened").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_closed:contains(xphone)").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_closed:contains(xpad)").toHaveCount(1);

    expect("tbody tr td:eq(2)").toHaveText("32");
});

test("correctly uses pivot_row_groupby key with default groupBy from the context", async () => {
    Partner._fields.amount = fields.Float();

    await mountView({
        type: "pivot",
        resModel: "partner",

        arch: `
				<pivot>
					<field name="customer" type="col"/>
					<field name="date" interval="day" type="row"/>
				</pivot>`,
        groupBy: ["customer"],
        context: {
            pivot_row_groupby: ["product_id"],
        },
    });

    expect("thead .o_pivot_header_cell_opened").toHaveCount(1);
    expect("thead .o_pivot_header_cell_closed:contains(First)").toHaveCount(1);
    expect("thead .o_pivot_header_cell_closed:contains(Second)").toHaveCount(1);

    // With pivot_row_groupby, groupBy customer should replace and eventually display product_id
    expect("tbody .o_pivot_header_cell_opened").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_closed:contains(xphone)").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_closed:contains(xpad)").toHaveCount(1);
});

test("pivot still handles __count__ measure", async () => {
    expect.assertions(4);

    Partner._fields.computed_field = fields.Integer({
        string: "Computed and not stored",
        aggregator: null,
        compute: () => 1,
        groupable: false,
    });
    Partner._fields.foo = fields.Integer({
        aggregator: null,
        groupable: false,
    });

    // for retro-compatibility reasons, the pivot view still handles
    // '__count__' measure.

    onRpc("formatted_read_grouping_sets", ({ kwargs }) => {
        expect(kwargs.aggregates).toEqual(["__count"]);
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot></pivot>",
        context: {
            pivot_measures: ["__count__"],
        },
    });

    await contains(".o_pivot_buttons button.dropdown-toggle").click();
    const dropdownMenu = getDropdownMenu(".o_pivot_buttons button.dropdown-toggle");
    expect(queryAll(".dropdown-item", { root: dropdownMenu })).toHaveLength(1);
    expect(queryOne(".dropdown-item")).toHaveText("Count");
    expect(queryOne(".dropdown-item")).toHaveClass("selected");
});

test("not use a many2one as a measure by default", async () => {
    expect.assertions(3);

    Partner._fields.computed_field = fields.Integer({
        string: "Computed and not stored",
        compute: () => 1,
        aggregator: null,
        groupable: false,
    });
    Partner._fields.foo = fields.Integer({
        aggregator: null,
        groupable: false,
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id"/>
				<field name="date" interval="month" type="col"/>
			</pivot>`,
    });
    await contains(".o_pivot_buttons button.dropdown-toggle").click();
    const dropdownMenu = getDropdownMenu(".o_pivot_buttons button.dropdown-toggle");
    expect(queryAll(".dropdown-item", { root: dropdownMenu })).toHaveLength(1);
    expect(queryText(".dropdown-item", { root: dropdownMenu })).toBe("Count");
    expect(queryOne(".dropdown-item", { root: dropdownMenu })).toHaveClass("selected");
});

test("pivot view with many2one field as a measure", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="measure"/>
				<field name="date" interval="month" type="col"/>
			</pivot>`,
    });

    expect(queryAllTexts("table tbody tr")).toEqual(["Total \n1\n \n1\n \n2\n \n2"]);
});

test("pivot view with reference field as a measure", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="reference" type="measure"/>
				<field name="date" interval="month" type="col"/>
			</pivot>`,
    });

    expect(queryAllTexts("table tbody tr")).toEqual(["Total \n1\n \n1\n \n2\n \n4"]);
});

test.tags("desktop");
test("m2o as measure, drilling down into data", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="measure"/>
			</pivot>`,
    });
    await contains("tbody .o_pivot_header_cell_closed").click();
    // click on date by month
    const dropdownMenu = getDropdownMenu("tbody .o_pivot_header_cell_closed");
    await contains(queryFirst(".dropdown-toggle", { root: dropdownMenu })).hover();
    await contains(queryOne(".o-dropdown-item:contains(Month)")).click();
    expect(queryAllTexts(".o_pivot_cell_value")).toEqual(["2", "1", "1", "2"]);
});

test("Row and column groupbys plus a domain", async () => {
    expect.assertions(3);

    const expectedContext = {
        group_by: [],
        pivot_column_groupby: ["customer"],
        pivot_measures: ["foo"],
        pivot_row_groupby: ["product_id"],
    };

    onRpc("create_filter", ({ args }) => {
        expect(args[0].context).toEqual(expectedContext);
        return true;
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter name="some_filter" string="Some Filter" domain="[('product_id', '=', 41)]"/>
			</search>`,
    });

    // Set a column groupby
    await contains("thead .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(1)").click();

    // Set a Row groupby
    await contains("tbody .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(4)").click();

    // Add a filter
    await toggleSearchBarMenu();
    await toggleMenuItem("Some Filter");

    expect("tbody .o_pivot_header_cell_closed").toHaveCount(1);
    expect("tbody .o_pivot_header_cell_closed").toHaveText("xpad");

    // Save current search to favorite
    await toggleSaveFavorite();
    await editFavoriteName("My favorite");
    await saveFavorite();
});

test("parallel data loading should discard all but the last one", async () => {
    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot>
					<field name="foo" type="measure"/>
				</pivot>`,
        searchViewArch: `
				<search>
					<filter string="Product" name="product_id" context="{'group_by':'product_id'}"/>
					<filter string="Customer" name="customer" context="{'group_by':'customer'}"/>
				</search>`,
    });

    expect(".o_pivot_cell_value").toHaveCount(1);
    expect("tbody tr").toHaveCount(1);

    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("Product");
    await toggleMenuItem("Customer");

    expect(".o_pivot_cell_value").toHaveCount(1);
    expect("tbody tr").toHaveCount(1);

    def.resolve();
    await animationFrame();

    expect(".o_pivot_cell_value").toHaveCount(6);
    expect("tbody tr").toHaveCount(6);
});

test("pivot measures should be alphabetically sorted", async () => {
    Partner._fields.computed_field = fields.Integer({
        string: "Computed and not stored",
        aggregator: null,
        compute: () => 1,
        groupable: false,
    });

    // It's important to compare capitalized and lowercased words
    // to be sure the sorting is effective with both of them
    Partner._fields.bouh = fields.Integer({ string: "bouh" });
    Partner._fields.modd = fields.Integer({ string: "modd" });
    Partner._fields.zip = fields.Integer({ string: "Zip" });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="zip" type="measure"/>
				<field name="foo" type="measure"/>
				<field name="bouh" type="measure"/>
				<field name="modd" type="measure"/>
			</pivot>`,
    });

    await contains(".o_pivot_buttons button.dropdown-toggle").click();
    expect(queryAllTexts(".o-dropdown--menu .dropdown-item")).toEqual([
        "bouh",
        "Foo",
        "modd",
        "Zip",
        "Count",
    ]);
});

test("pivot view should use default order for auto sorting", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot default_order="foo asc">
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    expect("thead th.o_pivot_measure_row").toHaveClass("o_pivot_sort_order_asc");
});

test("pivot view can be flipped", async () => {
    let rpcCount = 0;
    onRpc(() => {
        rpcCount++;
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="product_id" type="row"/>
			</pivot>`,
    });

    expect("tbody tr").toHaveCount(3);
    let values = ["4", "1", "3"];
    expect(getCurrentValues()).toBe(values.join());

    rpcCount = 0;
    await contains(".o_pivot_flip_button").click();

    expect(rpcCount).toBe(0);
    expect("tbody tr").toHaveCount(1, {
        message: "should have 1 rows: 1 for the main header",
    });

    values = ["1", "3", "4"];
    expect(getCurrentValues()).toBe(values.join());
});

test("Click on the measure list but not on a menu item", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        // have at least a measure to have a separator in the Measures dropdown:
        //
        // Foo
        // -----
        // Count
        arch: `<pivot><field name="foo" type="measure"/></pivot>`,
    });

    expect(".o-dropdown--menu").toHaveCount(0);

    // open the "Measures" menu
    await contains(".o_pivot_buttons .dropdown-toggle").click();
    expect(".o-dropdown--menu").toHaveCount(1);

    // click on the divider in the "Measures" menu does not crash
    await contains(".o-dropdown--menu .dropdown-divider").click();
    // the menu should still be open
    expect(".o-dropdown--menu").toHaveCount(1);

    // click on the measure list but not on a menu item or the separator
    await contains(".o-dropdown--menu").click();
    // the menu should still be open
    expect(".o-dropdown--menu").toHaveCount(1);
});

test.tags("desktop");
test("Navigation list view for a group and back with breadcrumbs", async () => {
    expect.assertions(6);

    Partner._views["pivot"] = `<pivot>
			<field name="customer" type="row"/>
		</pivot>`;
    Partner._views["search"] = `<search>
			<filter name="bayou" string="Bayou" domain="[('foo','=', 12)]"/>
		</search>`;
    Partner._views["list"] = `<list><field name="foo"/></list>`;
    Partner._views["form"] = `<form><field name="foo"/></form>`;

    let readGroupCount = 0;
    onRpc("formatted_read_grouping_sets", ({ kwargs }) => {
        expect.step("formatted_read_grouping_sets");
        const domain = kwargs.domain;
        if ([0].indexOf(readGroupCount) !== -1) {
            expect(domain).toEqual([]);
        } else if ([1, 2].indexOf(readGroupCount) !== -1) {
            expect(domain).toEqual([["foo", "=", 12]]);
        }
        readGroupCount++;
    });
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        const domain = kwargs.domain;
        expect(domain).toEqual(["&", ["foo", "=", 12], ["customer", "=", 1]]);
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("Bayou");
    await animationFrame();

    await contains(".o_pivot_cell_value:eq(1)").click();

    expect(".o_list_view").toHaveCount(1);

    await contains(".o_control_panel ol.breadcrumb li.breadcrumb-item").click();

    expect.verifySteps([
        "formatted_read_grouping_sets",
        "formatted_read_grouping_sets",
        "web_search_read",
        "formatted_read_grouping_sets",
    ]);
});

test("correctly compute group domain when a date field has false value", async () => {
    expect.assertions(1);

    Partner._records.forEach((r) => (r.date = false));

    mockDate("2016-12-20T1:00:00");

    mockService("action", {
        doAction(action) {
            expect(action.domain).toEqual([["date", "=", false]]);
            return Promise.resolve(true);
        },
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot o_enable_linking="1">
					<field name="date" interval="day" type="row"/>
				</pivot>`,
    });

    await contains(".o_value:eq(1)").click();
});

test("Does not identify 'false' with false as keys when creating group trees", async () => {
    Partner._fields.favorite_animal = fields.Char();
    Partner._records[0].favorite_animal = "Dog";
    Partner._records[1].favorite_animal = "false";
    Partner._records[2].favorite_animal = "None";

    mockDate("2016-12-20T1:00:00");

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot o_enable_linking="1">
					<field name="favorite_animal" type="row"/>
				</pivot>`,
    });

    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Count"]);
    expect(queryAllTexts("tbody th")).toEqual(["Total", "Dog", "None", "false", "None"]);
});

test("group bys added via control panel and expand Header do not stack", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot>
					<field name="foo" type="measure"/>
				</pivot>`,
    });

    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Foo"]);
    expect(queryAllTexts("tbody th")).toEqual(["Total"]);
    // open group by menu and add new groupby
    await toggleSearchBarMenu();
    await contains(`.o_add_custom_group_menu`).select("company_type");

    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Foo"]);
    expect(queryAllTexts("tbody th")).toEqual(["Total", "Company", "individual"]);

    // Set a Row groupby
    await contains("tbody tr:nth-child(2) .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .o_menu_item:nth-child(5)").click();

    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Foo"]);
    expect(queryAllTexts("tbody th")).toEqual(["Total", "Company", "xphone", "xpad", "individual"]);

    // open groupby menu generator and add a new groupby
    await toggleSearchBarMenu();
    await contains(`.o_add_custom_group_menu`).select("bar");

    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Foo"]);
    expect(queryAllTexts("tbody th")).toEqual([
        "Total",
        "Company",
        "Yes",
        "individual",
        "No",
        "Yes",
    ]);
});

test.tags("desktop");
test("display only one dropdown menu", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    // add a col groupby on Product
    await contains("thead th.o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item:eq(5)").click();

    // Click on the two header dropdown togglers
    await contains("thead th.o_pivot_header_cell_closed:eq(0)").click();
    await contains("thead th.o_pivot_header_cell_closed:eq(1)").click();

    expect(".o-dropdown--menu").toHaveCount(1);
});

test("Server order is kept by default", async () => {
    onRpc("formatted_read_grouping_sets", () => [
        [
            {
                "foo:sum": 32,
                __extra_domain: [],
                __count: 4,
            },
        ],
        [
            {
                customer: [2, "Second"],
                "foo:sum": 18,
                __count: 2,
                __extra_domain: [["customer", "=", 2]],
            },
            {
                customer: [1, "First"],
                "foo:sum": 14,
                __count: 2,
                __extra_domain: [["customer", "=", 1]],
            },
        ],
    ]);
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="customer" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
    });

    const values = [
        "32", // Total Value
        "18", // Second
        "14", // First
    ];
    expect(getCurrentValues()).toBe(values.join());
});

test("pivot rendering with boolean field", async () => {
    Partner._fields.bar = fields.Boolean({
        aggregator: "bool_or",
    });
    Partner._records = [
        { id: 1, bar: true, date: "2019-12-14" },
        { id: 2, bar: false, date: "2019-05-14" },
    ];

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="date" type="row" interval="day"/>
				<field name="bar" type="col"/>
				<field name="bar" string="SLA status Failed" type="measure"/>
			</pivot>`,
    });

    expect('tbody tr:contains("2019-12-14")').toHaveCount(1);
    expect('tbody tr:contains("2019-12-14") [type="checkbox"]').toBeChecked();
    expect('tbody tr:contains("2019-05-14")').toHaveCount(1);
    expect('tbody tr:contains("2019-05-14") [type="checkbox"]').not.toBeChecked();
});

test.tags("desktop");
test("empty pivot view with action helper", async () => {
    Partner._views["pivot"] = `<pivot>
		<field name="product_id" type="measure"/>
		<field name="date" interval="month" type="col"/>
	</pivot>`;
    Partner._views["search"] = `<search>
		<filter name="small_than_0" string="Small Than 0" domain="[('id', '&lt;', 0)]"/>
	</search>`;

    await mountView({
        type: "pivot",
        resModel: "partner",
        context: { search_default_small_than_0: true },
        noContentHelp: markup`<p class="abc">click to add a foo</p>`,
        config: {
            views: [[false, "search"]],
        },
    });

    expect(".o_view_nocontent .abc").toHaveCount(1);
    expect("table").toHaveCount(0);
    await removeFacet();
    expect(".o_view_nocontent .abc").toHaveCount(0);
    expect("table").toHaveCount(1);
});

test.tags("desktop");
test("empty pivot view with sample data", async () => {
    Partner._views["pivot"] = `<pivot sample="1">
		<field name="product_id" type="measure"/>
		<field name="date" interval="month" type="col"/>
	</pivot>`;
    Partner._views["search"] = `<search>
		<filter name="small_than_0" string="Small Than 0" domain="[('id', '&lt;', 0)]"/>
	</search>`;

    await mountView({
        type: "pivot",
        resModel: "partner",
        context: { search_default_small_than_0: true },
        noContentHelp: markup`<p class="abc">click to add a foo</p>`,
        config: {
            views: [[false, "search"]],
        },
    });

    expect(".o_pivot_view .o_content").toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent .abc").toHaveCount(1);
    await removeFacet();
    expect(".o_pivot_view .o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent .abc").toHaveCount(0);
    expect("table").toHaveCount(1);
});

test("non empty pivot view with sample data", async () => {
    Partner._views["pivot"] = `<pivot sample="1">
		<field name="product_id" type="measure"/>
		<field name="date" interval="month" type="col"/>
	</pivot>`;
    Partner._views["search"] = `<search>
		<filter name="small_than_0" string="Small Than 0" domain="[('id', '&lt;', 0)]"/>
	</search>`;

    await mountView({
        type: "pivot",
        resModel: "partner",
        noContentHelp: markup`<p class="abc">click to add a foo</p>`,
        config: {
            views: [[false, "search"]],
        },
    });

    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent .abc").toHaveCount(0);
    expect("table").toHaveCount(1);
    await toggleSearchBarMenu();
    await toggleMenuItem("Small Than 0");
    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent .abc").toHaveCount(1);
    expect("table").toHaveCount(0);
});

test.tags("desktop");
test("pivot is reloaded when leaving and coming back", async () => {
    Partner._views["pivot"] = `<pivot>
		<field name="customer" type="row"/>
	</pivot>`;
    Partner._views["list"] = `<list><field name="foo"/></list>`;

    onRpc("partner", "*", ({ method }) => {
        expect.step(method);
    });
    onRpc("/web/webclient/load_menus", () => {
        expect.step("/web/webclient/load_menus");
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "pivot"],
            [false, "list"],
        ],
    });

    expect(".o_pivot_view").toHaveCount(1);
    expect(getCurrentValues()).toBe(["4", "2", "2"].join(","));

    expect.verifySteps(["/web/webclient/load_menus", "get_views", "formatted_read_grouping_sets"]);

    // switch to list view
    await contains(".o_control_panel .o_switch_view.o_list").click();

    expect(".o_list_view").toHaveCount(1);
    expect.verifySteps(["web_search_read"]);

    // switch back to pivot
    await contains(".o_control_panel .o_switch_view.o_pivot").click();

    expect(".o_pivot_view").toHaveCount(1);
    expect(getCurrentValues()).toBe(["4", "2", "2"].join(","));

    expect.verifySteps(["formatted_read_grouping_sets"]);
});

test.tags("desktop");
test("expanded groups are kept when leaving and coming back", async () => {
    Partner._views["pivot"] = `<pivot>
		<field name="customer" type="row"/>
	</pivot>`;
    Partner._views["list"] = `<list><field name="foo"/></list>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "pivot"],
            [false, "list"],
        ],
    });

    expect(".o_pivot_view").toHaveCount(1);
    expect(getCurrentValues()).toBe(["4", "2", "2"].join(","));

    // drill down first row group (group by company_type)
    await contains("tbody .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item").click();

    expect(getCurrentValues()).toBe(["4", "2", "1", "1", "2"].join(","));

    // switch to list view
    await contains(".o_control_panel .o_switch_view.o_list").click();

    expect(".o_list_view").toHaveCount(1);

    // switch back to pivot
    await contains(".o_control_panel .o_switch_view.o_pivot").click();

    expect(".o_pivot_view").toHaveCount(1);
    expect(getCurrentValues()).toBe(["4", "2", "1", "1", "2"].join(","));
});

test.tags("desktop");
test("sorted rows are kept when leaving and coming back", async () => {
    Partner._views["pivot"] = `<pivot>
		<field name="foo" type="measure"/>
		<field name="product_id" type="row"/>
	</pivot>`;
    Partner._views["list"] = `<list><field name="foo"/></list>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "pivot"],
            [false, "list"],
        ],
    });

    expect(".o_pivot_view").toHaveCount(1);
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // sort the first group
    await contains("th.o_pivot_measure_row").click();
    await contains("th.o_pivot_measure_row").click();

    expect(getCurrentValues()).toBe(["32", "20", "12"].join(","));

    // switch to list view
    await contains(".o_control_panel .o_switch_view.o_list").click();

    expect(".o_list_view").toHaveCount(1);

    // switch back to pivot
    await contains(".o_control_panel .o_switch_view.o_pivot").click();

    expect(".o_pivot_view").toHaveCount(1);
    expect(getCurrentValues()).toBe(["32", "20", "12"].join(","));
});

test.tags("desktop");
test("correctly handle concurrent reloads", async () => {
    Partner._views["pivot"] = `<pivot>
		<field name="foo" type="measure"/>
		<field name="product_id" type="row"/>
	</pivot>`;
    Partner._views["list"] = `<list><field name="foo"/></list>`;

    let def;
    let readGroupCount = 0;
    onRpc("formatted_read_grouping_sets", () => {
        if (def) {
            readGroupCount++;
            if (readGroupCount === 2) {
                // slow down last formatted_read_grouping_sets of first reload
                return def;
            }
        }
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "pivot"],
            [false, "list"],
        ],
    });

    expect(".o_pivot_view").toHaveCount(1);
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // drill down first row group (group by company_type)
    await contains("tbody .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item").click();

    expect(getCurrentValues()).toBe(["32", "12", "12", "20"].join(","));

    // reload twice by clicking on pivot view switcher
    def = new Deferred();
    await contains(".o_control_panel .o_switch_view.o_pivot").click();
    await contains(".o_control_panel .o_switch_view.o_pivot").click();

    def.resolve();
    await animationFrame();

    expect(getCurrentValues()).toBe(["32", "12", "12", "20"].join(","));
});

test("consecutively toggle several measures", async () => {
    let def;
    Partner._fields.foo2 = fields.Integer({
        groupable: false,
    });
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
				<field name="product_id" type="row"/>
			</pivot>`,
    });

    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // Toggle several measures (the reload is blocked, so all measures should be toggled in once)
    def = new Deferred();
    await toggleMenu("Measures");
    await toggleMenuItem("Foo2"); // add foo2
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));
    await toggleMenuItem("Foo"); // remove foo
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));
    await toggleMenuItem("Count"); // add count
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    def.resolve();
    await animationFrame();

    expect(getCurrentValues()).toBe(["0", "4", "0", "1", "0", "3"].join(","));
});

test("flip axis while loading a filter", async () => {
    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
				<field name="date" type="col"/>
				<field name="product_id" type="row"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter name="my_filter" string="My Filter" domain="[('product_id', '=', 41)]"/>
			</search>`,
    });

    const values = ["2", "1", "29", "32", "12", "12", "2", "1", "17", "20"];
    expect(getCurrentValues()).toBe(values.join(","));

    // Set a domain (this reload is delayed)
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect(getCurrentValues()).toBe(values.join(","));

    // Flip axis
    await contains(".o_pivot_flip_button").click();
    expect(getCurrentValues()).toBe(values.join(","));

    def.resolve();
    await animationFrame();

    expect(getCurrentValues()).toBe(["20", "2", "1", "17"].join(","));
});

test("sort rows while loading a filter", async () => {
    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
				<field name="product_id" type="row"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter name="my_filter" string="My Filter" domain="[('product_id', '=', 41)]"/>
			</search>`,
    });

    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // Set a domain (this reload is delayed)
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // Sort rows (this operation should be ignored as it concerns the old
    // table, which will be replaced soon)
    await contains("th.o_pivot_measure_row").click();
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    def.resolve();
    await animationFrame();

    expect(getCurrentValues()).toBe(["20", "20"].join(","));
});

test("close a group while loading a filter", async () => {
    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",

        arch: `
			<pivot>
				<field name="foo" type="measure"/>
				<field name="product_id" type="row"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter name="my_filter" string="My Filter" domain="[('product_id', '=', 41)]"/>
			</search>`,
    });

    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // Set a domain (this reload is delayed)
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // Close a group (this operation should be ignored as it concerns the old
    // table, which will be replaced soon)
    await contains("tbody .o_pivot_header_cell_opened").click();
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    def.resolve();
    await animationFrame();

    expect(getCurrentValues()).toBe(["20", "20"].join(","));
});

test("add a groupby while loading a filter", async () => {
    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
				<field name="product_id" type="row"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter name="my_filter" string="My Filter" domain="[('product_id', '=', 41)]"/>
			</search>`,
    });

    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // Set a domain (this reload is delayed)
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // Add a groupby (this operation should be ignored as it concerns the old
    // table, which will be replaced soon)
    await contains("thead .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item").click();
    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    def.resolve();
    await animationFrame();

    expect(getCurrentValues()).toBe(["20", "20"].join(","));
});

test("expand a group while loading a filter", async () => {
    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",

        arch: `
			<pivot>
				<field name="foo" type="measure"/>
				<field name="product_id" type="row"/>
			</pivot>`,
        searchViewArch: `
			<search>
				<filter name="my_filter" string="My Filter" domain="[('product_id', '=', 41)]"/>
			</search>`,
    });

    // Add a groupby, to have a group to expand afterwards
    await contains("tbody .o_pivot_header_cell_closed").click();
    await contains(".o-dropdown--menu .dropdown-item").click();

    expect(getCurrentValues()).toBe(["32", "12", "12", "20"].join(","));

    // Set a domain (this reload is delayed)
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect(getCurrentValues()).toBe(["32", "12", "12", "20"].join(","));

    // Expand a group (this operation should be ignored as it concerns the old
    // table, which will be replaced soon)
    await contains("tbody .o_pivot_header_cell_closed:eq(1)").click();
    expect(getCurrentValues()).toBe(["32", "12", "12", "20"].join(","));

    def.resolve();
    await animationFrame();

    expect(getCurrentValues()).toBe(["20", "20"].join(","));
});

test("concurrent reloads: add a filter, and directly toggle a measure", async () => {
    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot>
					<field name="foo" type="measure"/>
					<field name="product_id" type="row"/>
				</pivot>`,
        searchViewArch: `
				<search>
					<filter name="my_filter" string="My Filter" domain="[('product_id', '=', 37)]"/>
				</search>`,
    });

    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // Set a domain (this reload is delayed)
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");

    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    // Toggle a measure
    await toggleMenu("Measures");
    await toggleMenuItem("Count");

    expect(getCurrentValues()).toBe(["32", "12", "20"].join(","));

    def.resolve();
    await animationFrame();

    expect(getCurrentValues()).toBe(["12", "1", "12", "1"].join(","));
});

test("if no measure is set in arch, 'Count' is used as measure initially", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot/>`,
    });

    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Count"]);
});

test("if (at least) one measure is set in arch and display_quantity is false or unset, 'Count' is not used as measure initially", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="foo" type="measure"/>
			</pivot>
		`,
    });

    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Foo"]);
});

test("if (at least) one measure is set in arch and display_quantity is true, 'Count' is used as measure initially", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot display_quantity="1">
				<field name="foo" type="measure"/>
			</pivot>
		`,
    });

    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Count", "Foo"]);
});

test("'Measures' menu when there is no measurable fields", async () => {
    delete Partner._fields.foo;
    delete Partner._fields.computed_field;

    Partner._records = [{ id: 1, display_name: "The one" }];

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot/>`,
    });

    await toggleMenu("Measures");

    // "Count" is the only measure available
    expect(queryAllTexts(".o-dropdown--menu .o_menu_item")).toEqual(["Count"]);
    // No separator should be displayed in the menu "Measures"
    expect(".o-dropdown--menu div.dropdown-divider").toHaveCount(0);
});

test("pivot_row_groupby should be also used after first load", async () => {
    const ids = [1, 2];
    const expectedContexts = [
        {
            group_by: ["bar"],
            pivot_column_groupby: [],
            pivot_measures: ["__count"],
            pivot_row_groupby: ["product_id"],
        },
        {
            group_by: ["bar", "customer"],
            pivot_column_groupby: [],
            pivot_measures: ["__count"],
            pivot_row_groupby: ["customer"],
        },
    ];

    onRpc("create_filter", ({ args }) => {
        expect(args[0].context).toEqual(expectedContexts.shift());
        return [ids.shift()];
    });

    await mountView({
        type: "pivot",
        resModel: "partner",

        arch: `<pivot/>`,
        searchViewArch: `
			<search>
				<filter name='product_id' string="Product" context="{'group_by':'product_id'}"/>
				<filter name='customer' string="Customer" context="{'group_by':'customer'}"/>
			</search>
		`,
        groupBy: ["bar"],
    });

    expect(queryAllTexts("th").slice(3)).toEqual(["Total", "No", "Yes"]);
    await contains("tbody th").click(); // click on row header "Total"
    await contains("tbody th").click(); // click on row header "Total"
    await contains(".o-dropdown--menu .o_menu_item").click(); // select "Product"
    expect(queryAllTexts("th").slice(3)).toEqual(["Total", "xphone", "xpad"]);
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("Favorite");
    await saveFavorite();
    expect(queryAllTexts("th").slice(3)).toEqual(["Total", "xphone", "xpad"]);
    await removeFacet();
    expect(queryAllTexts("th").slice(3)).toEqual(["Total", "No", "Yes"]);
    await toggleSearchBarMenu();
    await toggleMenuItem("Favorite");
    expect(queryAllTexts("th").slice(3)).toEqual(["Total", "xphone", "xpad"]);
    await toggleMenuItem("customer");
    expect(queryAllTexts("th").slice(3)).toEqual([
        "Total",
        "xphone",
        "First",
        "xpad",
        "First",
        "Second",
    ]);
    await contains("tbody th").click(); // click on row header "Total"
    await contains("tbody th").click(); // click on row header "Total"
    await contains(".o-dropdown--menu .o_menu_item:eq(1)").click(); // select "Customer"
    expect(queryAllTexts("th").slice(3)).toEqual(["Total", "First", "Second"]);
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("Favorite 2");
    await saveFavorite();
    expect(queryAllTexts("th").slice(3)).toEqual(["Total", "First", "Second"]);
});

test("pivot_row_groupby should be also used after first load (2)", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        groupBy: ["product_id"],
        arch: `<pivot/>`,
        irFilters: [
            {
                user_ids: [2],
                name: "Favorite",
                id: 1,
                context: `
						{
							"group_by": [],
							"pivot_row_groupby": ["customer"],
							"pivot_col_groupby": [],
							"pivot_measures": ["foo"],
						}
					`,
                sort: "[]",
                domain: "",
                is_default: false,
                model_id: "foo",
                action_id: false,
            },
        ],
    });

    expect(queryAllTexts("th").slice(3)).toEqual(["Total", "xphone", "xpad"]);
    await toggleSearchBarMenu();
    await toggleMenuItem("Favorite");
    expect(queryAllTexts("th").slice(3)).toEqual(["Total", "First", "Second"]);
});

test("specific pivot keys in action context must have less importance than in favorite context", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",

        arch: `<pivot/>`,
        context: {
            pivot_column_groupby: [],
            pivot_measures: ["__count"],
            pivot_row_groupby: [],
        },
        irFilters: [
            {
                user_ids: [2],
                name: "My favorite",
                id: 1,
                context: `{
						"pivot_column_groupby": ["bar"],
						"pivot_measures": ["computed_field"],
						"pivot_row_groupby": [],
					}`,
                sort: "[]",
                domain: "",
                is_default: true,
                model_id: "partner",
                action_id: false,
            },
            {
                user_ids: [2],
                name: "My favorite 2",
                id: 2,
                context: `{
						"pivot_column_groupby": ["product_id"],
						"pivot_measures": ["computed_field", "__count"],
						"pivot_row_groupby": [],
					}`,
                sort: "[]",
                domain: "",
                is_default: false,
                model_id: "partner",
                action_id: false,
            },
        ],
    });

    expect(queryAllTexts("th").slice(1, 6)).toEqual([
        "Total",
        "",
        "No",
        "Yes",
        "Computed and not stored",
    ]);
    await toggleSearchBarMenu();
    await toggleMenuItem("My favorite 2");
    expect(queryAllTexts("th").slice(1, 11)).toEqual([
        "Total",
        "",
        "xphone",
        "xpad",
        "Computed and not stored",
        "Count",
        "Computed and not stored",
        "Count",
        "Computed and not stored",
        "Count",
    ]);
});

test("favorite pivot_measures should be used even if found also in global context", async () => {
    // Computed and not stored displayed in "Measures" menu
    Partner._fields.computed_field = fields.Integer({
        string: "Computed and not stored",
        compute: () => 1,
        store: true,
        groupable: false,
    });

    onRpc("create_filter", ({ args }) => {
        expect(args[0].context).toEqual({
            group_by: [],
            pivot_column_groupby: [],
            pivot_measures: ["computed_field"],
            pivot_row_groupby: [],
        });
        return [1];
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot/>`,
        context: {
            pivot_measures: ["__count"],
        },
    });

    expect(queryAllTexts("th").slice(1, 3)).toEqual(["Total", "Count"]);
    await toggleMenu("Measures");
    await toggleMenuItem("Count");
    await toggleMenuItem("Computed and not stored");
    expect(getFacetTexts()).toEqual([]);
    expect(queryAllTexts("th").slice(1, 3)).toEqual(["Total", "Computed and not stored"]);
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("Favorite");
    await saveFavorite();
    expect(getFacetTexts()).toEqual(["Favorite"]);
    expect(queryAllTexts("th").slice(1, 3)).toEqual(["Total", "Computed and not stored"]);
});

test.tags("desktop");
test("filter -> sort -> unfilter should not crash", async () => {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot>
					<field name="product_id" type="row"/>
					<field name="bar" type="row"/>
				</pivot>
			`,
        searchViewArch: `
			<search>
				<filter name="xphone" domain="[('product_id', '=', 37)]" />
			</search>
		`,
        context: {
            search_default_xphone: true,
        },
    });

    expect(getFacetTexts()).toEqual(["xphone"]);
    expect(queryAllTexts("tbody th")).toEqual(["Total", "xphone", "Yes"]);
    expect(getCurrentValues()).toBe(["1", "1", "1"].join());
    await contains(".o_pivot_measure_row").click();
    await toggleSearchBarMenu();
    await toggleMenuItem("xphone");
    expect(getFacetTexts()).toEqual([]);
    expect(queryAllTexts("tbody th")).toEqual(["Total", "xphone", "Yes", "xpad"]);
    expect(getCurrentValues()).toBe(["4", "1", "1", "3"].join());
});

test("no class 'o_view_sample_data' when real data are presented", async () => {
    Partner._records = [];
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot sample="1">
					<field name="product_id" type="row"/>
				</pivot>
			`,
    });

    expect(".o_pivot_view .o_view_sample_data").toHaveCount(1);
    expect(".o_pivot_view table").toHaveCount(1);
    await toggleMenu("Measures");
    await toggleMenuItem("Foo");
    expect(".o_pivot_view .o_view_sample_data").toHaveCount(0);
    expect(".o_pivot_view table").toHaveCount(0);
});

test("group by properties in pivot view", async () => {
    onRpc("partner", "web_search_read", ({ kwargs }) => {
        if (kwargs.specification?.properties_definition) {
            expect.step("fetch_definition");
        }
    });
    onRpc("partner", "formatted_read_grouping_sets", ({ kwargs, method }) => {
        if (kwargs.grouping_sets[0].includes("properties.my_char")) {
            expect.step(method);
            return [
                [
                    {
                        "properties.my_char": false,
                        __extra_domain: [["properties.my_char", "=", false]],
                        __count: 2,
                    },
                    {
                        "properties.my_char": "aaa",
                        __extra_domain: [["properties.my_char", "=", "aaa"]],
                        __count: 1,
                    },
                    {
                        "properties.my_char": "bbb",
                        __extra_domain: [["properties.my_char", "=", "bbb"]],
                        __count: 1,
                    },
                ],
            ];
        }
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: "<pivot/>",
        searchViewArch: `
			<search>
				<filter name='group_by_properties' string="Properties" context="{'group_by':'properties'}"/>
			</search>
		`,
    });

    expect(".o_value").toHaveCount(1);
    expect(".o_value").toHaveText("4");

    await contains(".border-top-0 span").click();
    expect.verifySteps([]);

    expect(".o_accordion_toggle").toHaveText("Properties");
    await contains(".o_accordion_toggle:contains(Properties)").click();

    await animationFrame();
    expect.verifySteps(["fetch_definition"]);

    await contains(".o_accordion_values .o_menu_item").click();

    await animationFrame();
    expect.verifySteps(["formatted_read_grouping_sets"]);

    const cells = queryAll(".o_value");
    expect(cells).toHaveLength(4);
    expect(cells[0]).toHaveText("2");
    expect(cells[1]).toHaveText("1");
    expect(cells[2]).toHaveText("1");
    expect(cells[3]).toHaveText("4");

    const columns = queryAll(".o_pivot_header_cell_closed");
    expect(columns).toHaveLength(4);
    expect(columns[0]).toHaveText("None");
    expect(columns[1]).toHaveText("aaa");
    expect(columns[2]).toHaveText("bbb");
});

test("avoid duplicates grouping_sets in formatted_read_grouping_sets", async () => {
    onRpc("formatted_read_grouping_sets", ({ kwargs }) => {
        expect(kwargs.grouping_sets).toEqual([[], ["bar"], ["bar", "date:month"], ["date:month"]]);
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
				<pivot sample="1">
					<field name="date" type="row" interval="month"/>
					<field name="bar" type="row"/>
					<field name="bar" type="col"/>
					<field name="date" type="col" interval="month"/>
				</pivot>
			`,
    });
});

test("Close header dropdown when a simple groupby is selected", async function (assert) {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot/>`,
    });
    expect(".o-overlay-container .dropdown-menu").toHaveCount(0);
    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Count"]);

    await contains("thead .o_pivot_header_cell_closed").click();
    expect(".o-overlay-container .dropdown-menu").toHaveCount(1);

    await contains(".o-overlay-container .o-dropdown--menu .dropdown-item").click();
    expect(".o-overlay-container .dropdown-menu").toHaveCount(0);
    expect(queryAllTexts("thead th")).toEqual([
        "",
        "Total",
        "",
        "Company",
        "individual",
        "Count",
        "Count",
        "Count",
    ]);
});

test.tags("desktop");
test("Close header dropdown when a simple date groupby option is selected", async function (assert) {
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot/>`,
    });
    expect(".o-overlay-container .dropdown-menu").toHaveCount(0);
    expect(queryAllTexts("thead th")).toEqual(["", "Total", "Count"]);

    await contains("thead .o_pivot_header_cell_closed").click();
    expect(".o-overlay-container .dropdown-menu").toHaveCount(1);

    // open the Date sub dropdown
    await contains(".o-dropdown--menu .dropdown-toggle.o_menu_item").hover();
    const subDropdownMenu = getDropdownMenu(".o-dropdown--menu .dropdown-toggle.o_menu_item");

    await contains(queryOne(".dropdown-item:eq(2)", { root: subDropdownMenu })).click();
    expect(".o-overlay-container .dropdown-menu").toHaveCount(0);
    expect(queryAllTexts("thead th")).toEqual([
        "",
        "Total",
        "",
        "April 2016",
        "October 2016",
        "December 2016",
        "Count",
        "Count",
        "Count",
        "Count",
    ]);
});

test("missing property field definition is fetched", async function () {
    onRpc(({ method, kwargs }) => {
        if (method === "formatted_read_grouping_sets") {
            expect.step(JSON.stringify(kwargs.grouping_sets));
            return [
                [
                    {
                        __extra_domain: [],
                        __count: 3,
                    },
                ],
                [
                    {
                        "properties.my_char": false,
                        __extra_domain: [["properties.my_char", "=", false]],
                        __count: 2,
                    },
                    {
                        "properties.my_char": "aaa",
                        __extra_domain: [["properties.my_char", "=", "aaa"]],
                        __count: 1,
                    },
                ],
            ];
        } else if (method === "get_property_definition") {
            return {
                name: "my_char",
                type: "char",
            };
        }
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot/>`,
        irFilters: [
            {
                user_ids: [2],
                name: "My Filter",
                id: 5,
                context: `{"group_by": ['properties.my_char']}`,
                sort: "[]",
                domain: "[]",
                is_default: true,
                model_id: "partner",
                action_id: false,
            },
        ],
    });
    expect.verifySteps([`[[],["properties.my_char"]]`]);
    expect(getCurrentValues()).toBe("3,2,1");
});

test("missing deleted property field definition is created", async function (assert) {
    onRpc(({ method, kwargs }) => {
        if (method === "formatted_read_grouping_sets") {
            expect.step(JSON.stringify(kwargs.grouping_sets));
            return [
                [
                    {
                        __extra_domain: [],
                        __count: 3,
                    },
                ],
                [
                    {
                        "properties.my_char": false,
                        __extra_domain: [["properties.my_char", "=", false]],
                        __count: 2,
                    },
                    {
                        "properties.my_char": "aaa",
                        __extra_domain: [["properties.my_char", "=", "aaa"]],
                        __count: 1,
                    },
                ],
            ];
        } else if (method === "get_property_definition") {
            return {};
        }
    });
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `<pivot/>`,
        irFilters: [
            {
                user_ids: [2],
                name: "My Filter",
                id: 5,
                context: `{"group_by": ['properties.my_char']}`,
                sort: "[]",
                domain: "[]",
                is_default: true,
                model_id: "partner",
                action_id: false,
            },
        ],
    });
    expect.verifySteps([`[[],["properties.my_char"]]`]);
    expect(getCurrentValues()).toBe("3,2,1");
});

test("middle clicking on a cell triggers a doAction", async () => {
    expect.assertions(3);
    Partner._views["form,2"] = `<form/>`;
    Partner._views["kanban,5"] = `<kanban/>`;

    mockService("action", {
        doAction(action, options) {
            expect(action).toEqual({
                context: {
                    lang: "en",
                    tz: "taht",
                    someKey: true,
                    uid: 7,
                    allowed_company_ids: [1],
                },
                domain: [["product_id", "=", 37]],
                name: "Partners",
                res_model: "partner",
                target: "current",
                type: "ir.actions.act_window",
                view_mode: "list",
                views: [
                    [false, "list"],
                    [2, "form"],
                ],
            });
            expect(options).toEqual({
                newWindow: true,
            });
            return Promise.resolve(true);
        },
    });

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot string="Partners">
				<field name="product_id" type="row"/>
				<field name="foo" type="measure"/>
			</pivot>`,
        context: { someKey: true, search_default_test: 3 },
        config: {
            views: [
                [2, "form"],
                [5, "kanban"],
                [false, "list"],
                [false, "pivot"],
            ],
        },
    });

    expect("table").toHaveClass("o_enable_linking");
    await contains(".o_pivot_cell_value:eq(1)").click({ ctrlKey: true }); // should trigger a do_action
});

test("display '0' for false group, when grouped by int field", async () => {
    Partner._records[0].foo = false;

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
            <pivot>
                <field name="foo" type="row"/>
            </pivot>`,
        groupBy: ["foo"],
    });

    expect(queryAllTexts("tbody th")).toEqual(["Total", "1", "2", "17", "0"]);
});

test("display the field's falsy_value_label for false group, if defined", async () => {
    Partner._fields.product_id.falsy_value_label = "I'm the false group";
    Partner._records[0].product_id = false;

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
            <pivot>
                <field name="foo" type="row"/>
            </pivot>`,
        groupBy: ["product_id"],
    });

    expect(queryAllTexts("tbody th")).toEqual(["Total", "xpad", "I'm the false group"]);
});

test.tags("desktop");
test("pivot views make their control panel available directly", async () => {
    const def = new Deferred();
    onRpc("formatted_read_grouping_sets", () => def);
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
            <pivot>
                <field name="foo" type="row"/>
            </pivot>`,
        groupBy: ["product_id"],
    });

    expect(".o_pivot_view").toHaveCount(1);
    expect(".o_pivot_view .o_control_panel .o_searchview").toHaveCount(1);
    expect(".o_pivot_view .o_pivot").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o_pivot_view .o_pivot").toHaveCount(1);
});

test("pivot view with monetary with multiple currencies", async () => {
    Partner._fields.amount = fields.Monetary({ currency_field: "currency_id" });
    Partner._fields.currency_id = fields.Many2one({ relation: "res.currency", default: 1 });
    Partner._records[0].amount = 500;
    Partner._records[1].amount = 300;
    Partner._records[2].amount = 200;
    Partner._records[3].amount = 400;
    Partner._records[3].currency_id = 2;
    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: `
			<pivot>
				<field name="amount" type="measure"/>
			</pivot>`,
        groupBy: ["currency_id"],
    });
    expect(".o_pivot table tbody tr").toHaveCount(3);
    expect(".o_pivot table tbody tr:first").toHaveText("Total \n$ 1,400.00?");
    expect(".o_pivot table tbody tr:eq(1)").toHaveText("USD \n$ 1,000.00");
    expect(".o_pivot table tbody tr:last").toHaveText("EUR \n400.00 €");

    // multi currencies popover
    await toggleMultiCurrencyPopover(".o_pivot table tbody tr:first .o_value sup");
    expect(".o_multi_currency_popover").toHaveCount(1);
    expect(".o_multi_currency_popover").toHaveText("2,800.00 € at $ 0.50");

    // test sorting
    await contains("th.o_pivot_measure_row").click();
    expect(".o_pivot table tbody tr:eq(1)").toHaveText("EUR \n400.00 €");
    expect(".o_pivot table tbody tr:last").toHaveText("USD \n$ 1,000.00");
    await contains("th.o_pivot_measure_row").click();
    expect(".o_pivot table tbody tr:eq(1)").toHaveText("USD \n$ 1,000.00");
    expect(".o_pivot table tbody tr:last").toHaveText("EUR \n400.00 €");
});

test.tags("desktop");
test("scroll position is restored when coming back to pivot view", async () => {
    Partner._views = {
        kanban: `
            <pivot>
                <field name="foo" type="row"/>
            </pivot>`,
        list: `<list><field name="foo"/></list>`,
        search: `<search />`,
    };

    for (let i = 1; i < 20; i++) {
        Partner._records.push({ id: 100 + i, foo: 100 + i });
    }

    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await resize({ width: 800, height: 300 });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "pivot"],
            [false, "list"],
        ],
        context: {
            group_by: ["foo"],
        },
    });

    expect(".o_pivot_view").toHaveCount(1);
    // simulate a scroll in the pivot view
    queryOne(".o_content").scrollTop = 200;

    await getService("action").switchView("list");
    expect(".o_list_view").toHaveCount(1);

    // the pivot is "lazy", so it displays the control panel directly, and the renderer later with
    // the data => simulate this and check that the scroll position is correctly restored
    def = new Deferred();
    await getService("action").switchView("pivot");
    expect(".o_pivot_view").toHaveCount(1);
    expect(".o_content .o_pivot").toHaveCount(0);
    def.resolve();
    await animationFrame();
    expect(".o_content .o_pivot").toHaveCount(1);
    expect(".o_content").toHaveProperty("scrollTop", 200);
});

test.tags("mobile");
test("scroll position is restored when coming back to pivot view (mobile)", async () => {
    Partner._views = {
        kanban: `
            <pivot>
                <field name="foo" type="row"/>
            </pivot>`,
        list: `<list><field name="foo"/></list>`,
        search: `<search />`,
    };

    for (let i = 1; i < 20; i++) {
        Partner._records.push({ id: 100 + i, foo: 100 + i });
    }

    let def;
    onRpc("formatted_read_grouping_sets", () => def);
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "pivot"],
            [false, "list"],
        ],
        context: {
            group_by: ["foo"],
        },
    });

    expect(".o_pivot_view").toHaveCount(1);
    // simulate a scroll in the pivot view
    queryOne(".o_pivot_view").scrollTop = 200;

    await getService("action").switchView("list");
    expect(".o_list_view").toHaveCount(1);

    // the pivot is "lazy", so it displays the control panel directly, and the renderer later with
    // the data => simulate this and check that the scroll position is correctly restored
    def = new Deferred();
    await getService("action").switchView("pivot");
    expect(".o_pivot_view").toHaveCount(1);
    expect(".o_content .o_pivot").toHaveCount(0);
    def.resolve();
    await animationFrame();
    expect(".o_content .o_pivot").toHaveCount(1);
    expect(".o_pivot_view").toHaveProperty("scrollTop", 200);
});
