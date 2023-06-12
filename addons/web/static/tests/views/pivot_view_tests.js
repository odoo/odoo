/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import {
    click,
    getFixture,
    legacyExtraNextTick,
    makeDeferred,
    mockDownload,
    nextTick,
    patchDate,
    patchWithCleanup,
    triggerEvent,
    triggerEvents,
    mouseEnter,
} from "../helpers/utils";
import {
    applyGroup,
    editFavoriteName,
    getFacetTexts,
    removeFacet,
    saveFavorite,
    selectGroup,
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
    toggleAddCustomGroup,
    toggleComparisonMenu,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
} from "../search/helpers";
import { createWebClient, doAction } from "../webclient/helpers";
import { makeView } from "./helpers";
import { browser } from "@web/core/browser/browser";

const serviceRegistry = registry.category("services");

import { markup } from "@odoo/owl";

/**
 * Helper function that returns, given a pivot instance, the values of the
 * table, separated by ','.
 *
 * @returns {string}
 */
function getCurrentValues(el) {
    return [...el.querySelectorAll(".o_pivot_cell_value div")].map((el) => el.innerText).join();
}

let serverData;
let target;
QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "integer",
                            searchable: true,
                            group_operator: "sum",
                        },
                        bar: { string: "bar", type: "boolean", store: true, sortable: true },
                        date: { string: "Date", type: "date", store: true, sortable: true },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            store: true,
                            sortable: true,
                        },
                        other_product_id: {
                            string: "Other Product",
                            type: "many2one",
                            relation: "product",
                            store: true,
                            sortable: true,
                        },
                        non_stored_m2o: {
                            string: "Non Stored M2O",
                            type: "many2one",
                            relation: "product",
                        },
                        customer: {
                            string: "Customer",
                            type: "many2one",
                            relation: "customer",
                            store: true,
                            sortable: true,
                        },
                        computed_field: {
                            string: "Computed and not stored",
                            type: "integer",
                            compute: true,
                            group_operator: "sum",
                        },
                        company_type: {
                            string: "Company Type",
                            type: "selection",
                            selection: [
                                ["company", "Company"],
                                ["individual", "individual"],
                            ],
                            searchable: true,
                            sortable: true,
                            store: true,
                        },
                        price_nonaggregatable: {
                            string: "Price non-aggregatable",
                            type: "monetary",
                            group_operator: undefined,
                            store: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: 12,
                            bar: true,
                            date: "2016-12-14",
                            product_id: 37,
                            customer: 1,
                            computed_field: 19,
                            company_type: "company",
                        },
                        {
                            id: 2,
                            foo: 1,
                            bar: true,
                            date: "2016-10-26",
                            product_id: 41,
                            customer: 2,
                            computed_field: 23,
                            company_type: "individual",
                        },
                        {
                            id: 3,
                            foo: 17,
                            bar: true,
                            date: "2016-12-15",
                            product_id: 41,
                            customer: 2,
                            computed_field: 26,
                            company_type: "company",
                        },
                        {
                            id: 4,
                            foo: 2,
                            bar: false,
                            date: "2016-04-11",
                            product_id: 41,
                            customer: 1,
                            computed_field: 19,
                            company_type: "individual",
                        },
                    ],
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char" },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
                customer: {
                    fields: {
                        name: { string: "Customer Name", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "First",
                        },
                        {
                            id: 2,
                            display_name: "Second",
                        },
                    ],
                },
            },
        };
        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("user", makeFakeUserService());
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
    });

    QUnit.module("PivotView");

    QUnit.test("simple pivot rendering", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="measure"/>
                </pivot>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    assert.strictEqual(
                        args.kwargs.lazy,
                        false,
                        "the read_group should be done with the lazy=false option"
                    );
                }
            },
        });

        assert.hasClass(target.querySelector(".o_pivot_view"), "o_view_controller");
        assert.hasClass(target.querySelector("table"), "o_enable_linking");
        assert.containsOnce(
            target,
            "td.o_pivot_cell_value:contains(32)",
            "should contain a pivot cell with the sum of all records"
        );
    });

    QUnit.test("pivot rendering with widget", async function (assert) {
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="measure" widget="float_time"/>
                </pivot>`,
        });

        assert.containsOnce(
            target,
            "td.o_pivot_cell_value:contains(32:00)",
            "should contain a pivot cell with the sum of all records"
        );
    });

    QUnit.test("pivot rendering with string attribute on field", async function (assert) {
        serverData.models.partner.fields.foo = {
            string: "Foo",
            type: "integer",
            store: true,
            group_operator: "sum",
        };

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot string="Partners">
                    <field name="foo" string="BAR" type="measure"/>
                </pivot>`,
        });

        await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));
        assert.strictEqual(
            target.querySelector(".o_cp_bottom_left .dropdown-menu .dropdown-item").innerText,
            "BAR"
        );
        assert.strictEqual(
            target.querySelector(".o_pivot_measure_row").innerText,
            "BAR",
            "the displayed name should be the one set in the string attribute"
        );
    });

    QUnit.test("Pivot with integer row group by with 0 as header", async function (assert) {
        serverData.models.partner.records[0].foo = 0;
        serverData.models.partner.records[1].foo = 0;
        serverData.models.partner.records[2].foo = 0;
        serverData.models.partner.records[3].foo = 0;

        const pivot = await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="measure"/>
                    <field name="foo" type="row"/>
                </pivot>`,
        });
        const { rows } = pivot.model.getTable();
        assert.strictEqual(rows.length, 2);
        assert.strictEqual(rows[0].title, "Total");
        assert.strictEqual(rows[1].title, 0);
    });

    QUnit.test("Pivot with integer col group by with 0 as header", async function (assert) {
        serverData.models.partner.records[0].foo = 0;
        serverData.models.partner.records[1].foo = 0;
        serverData.models.partner.records[2].foo = 0;
        serverData.models.partner.records[3].foo = 0;

        const pivot = await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="measure"/>
                    <field name="foo" type="col"/>
                </pivot>`,
        });
        const { headers } = pivot.model.getTable();
        assert.strictEqual(headers[1][0].title, 0);
    });

    QUnit.test(
        "pivot rendering with string attribute on non stored field",
        async function (assert) {
            serverData.models.partner.fields.fubar = {
                string: "Fubar",
                type: "integer",
                store: false,
                group_operator: "sum",
            };

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                <pivot string="Partners">
                    <field name="fubar" string="fubar" type="measure"/>
                </pivot>`,
            });
            assert.strictEqual(
                target.querySelector(".o_pivot_measure_row").innerText,
                "fubar",
                "the displayed name should be the one set in the string attribute"
            );
        }
    );

    QUnit.test("pivot rendering with invisible attribute on field", async function (assert) {
        // when invisible, a field should neither be an active measure nor be a selectable measure
        Object.assign(serverData.models.partner.fields, {
            foo: { string: "Foo", type: "integer", store: true, group_operator: "sum" },
            foo2: { string: "Foo2", type: "integer", store: true, group_operator: "sum" },
        });

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="measure"/>
                    <field name="foo2" type="measure" invisible="1"/>
                </pivot>`,
        });

        // there should be only one displayed measure as the other one is invisible
        assert.containsOnce(target, ".o_pivot_measure_row");
        await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));
        // there should be only one measure besides count, as the other one is invisible
        assert.containsN(target, ".o_cp_bottom_left .dropdown-menu .dropdown-item", 2);
        // the invisible field souldn't be in the groupable fields neither
        await click(target.querySelector(".o_pivot_header_cell_closed"));
        assert.containsNone(target, '.dropdown-menu a[data-field="foo2"]');
    });

    QUnit.test('pivot view without "string" attribute', async function (assert) {
        assert.expect(1);

        const pivot = await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        // this is important for export functionality.
        assert.strictEqual(
            pivot.model.metaData.title.toString(),
            pivot.env._t("Untitled"),
            "should have a valid title"
        );
    });

    QUnit.test("group headers should have a tooltip", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="date" type="row"/>
                </pivot>`,
        });

        assert.strictEqual(
            target.querySelectorAll("tbody .o_pivot_header_cell_closed")[0].dataset.tooltip,
            "Date"
        );
        assert.strictEqual(
            target.querySelectorAll("thead .o_pivot_header_cell_closed")[1].dataset.tooltip,
            "Product"
        );
    });

    QUnit.test(
        "pivot view add computed fields explicitly defined as measure",
        async function (assert) {
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                <pivot>
                    <field name="computed_field" type="measure"/>
                </pivot>`,
            });

            await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));
            assert.containsOnce(
                target,
                ".o_cp_bottom_left .dropdown-menu .dropdown-item:contains(Computed and not stored)"
            );
            assert.strictEqual(
                target.querySelector(".o_pivot_measure_row").innerText,
                "Computed and not stored"
            );
        }
    );

    QUnit.test(
        "pivot view do not add number field without group_operator",
        async function (assert) {
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                <pivot>
                    <field name="price_nonaggregatable"/>
                </pivot>`,
            });

            await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));
            assert.containsNone(
                target,
                ".o_cp_bottom_left .dropdown-menu .dropdown-item:contains(Price non-aggregatable)"
            );
        }
    );

    QUnit.test("clicking on a cell triggers a doAction", async function (assert) {
        assert.expect(2);

        serverData.views = {
            "partner,2,form": "<form/>",
            "partner,false,list": "<list/>",
            "partner,5,kanban": "<kanban/>",
        };
        patchWithCleanup(session, {
            user_context: { userContextKey: true },
        });
        const fakeActionService = {
            start() {
                return {
                    doAction(action) {
                        assert.deepEqual(
                            action,
                            {
                                context: { someKey: true, uid: 7, userContextKey: true },
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
                            },
                            "should trigger do_action with the correct args"
                        );
                        return Promise.resolve(true);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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

        assert.hasClass(target.querySelector("table"), "o_enable_linking");
        await click(target.querySelectorAll(".o_pivot_cell_value")[1]); // should trigger a do_action
    });

    QUnit.test("row and column are highlighted when hovering a cell", async function (assert) {
        assert.expect(11);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="col"/>
                    <field name="product_id" type="row"/>
                </pivot>`,
        });

        // check row highlighting
        assert.hasClass(
            target.querySelector("table"),
            "table-hover",
            "with className 'table-hover', rows are highlighted (bootstrap)"
        );

        // check column highlighting
        // hover third measure
        await triggerEvents(target, "th.o_pivot_measure_row:nth-of-type(3)", ["mouseover"]);
        assert.containsN(target, ".o_cell_hover", 3);
        for (var i = 1; i <= 3; i++) {
            assert.hasClass(
                target.querySelector(`tbody tr:nth-of-type(${i}) td:nth-of-type(3)`),
                "o_cell_hover"
            );
        }
        await triggerEvents(target, "th.o_pivot_measure_row:nth-of-type(3)", ["mouseout"]);
        assert.containsNone(target, ".o_cell_hover");

        // hover second cell, second row
        await triggerEvents(target, "tbody tr:nth-of-type(1) td:nth-of-type(2)", ["mouseover"]);
        assert.containsN(target, ".o_cell_hover", 3);
        for (i = 1; i <= 3; i++) {
            assert.hasClass(
                target.querySelector(`tbody tr:nth-of-type(${i}) td:nth-of-type(2)`),
                "o_cell_hover"
            );
        }
        await triggerEvents(target, "tbody tr:nth-of-type(2) td:nth-of-type(2)", ["mouseout"]);
        assert.containsNone(target, ".o_cell_hover");
    });

    QUnit.test("columns are highlighted when hovering a measure", async function (assert) {
        assert.expect(15);

        patchDate(2016, 11, 20, 1, 0, 0);

        serverData.models.partner.records[0].date = "2016-11-15";
        serverData.models.partner.records[1].date = "2016-12-17";
        serverData.models.partner.records[2].date = "2016-11-22";
        serverData.models.partner.records[3].date = "2016-11-03";

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="date" type="col"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="date_filter" date="date" domain="[]" default_period='this_month'/>
                </search>`,
            context: { search_default_date_filter: true },
        });

        await toggleComparisonMenu(target);
        await toggleMenuItem(target, "Date: Previous period");

        // hover Count in first group
        await triggerEvents(target, "th.o_pivot_measure_row:nth-of-type(1)", ["mouseover"]);
        assert.containsN(target, ".o_cell_hover", 3);
        for (let i = 1; i <= 3; i++) {
            assert.hasClass(
                target.querySelector(`tbody tr:nth-of-type(${i}) td:nth-of-type(1)`),
                "o_cell_hover"
            );
        }
        await triggerEvents(target, "th.o_pivot_measure_row:nth-of-type(1)", ["mouseout"]);
        assert.containsNone(target, ".o_cell_hover");

        // hover Count in second group
        await triggerEvents(target, "th.o_pivot_measure_row:nth-of-type(2)", ["mouseover"]);
        assert.containsN(target, ".o_cell_hover", 3);
        for (let i = 1; i <= 3; i++) {
            assert.hasClass(
                target.querySelector(`tbody tr:nth-of-type(${i}) td:nth-of-type(4)`),
                "o_cell_hover"
            );
        }
        await triggerEvents(target, "th.o_pivot_measure_row:nth-of-type(2)", ["mouseout"]);
        assert.containsNone(target, ".o_cell_hover");

        // hover Count in total column
        await triggerEvents(target, "th.o_pivot_measure_row:nth-of-type(3)", ["mouseover"]);
        assert.containsN(target, ".o_cell_hover", 3);
        for (let i = 1; i <= 3; i++) {
            assert.hasClass(
                target.querySelector(`tbody tr:nth-of-type(${i}) td:nth-of-type(7)`),
                "o_cell_hover"
            );
        }
        await triggerEvents(target, "th.o_pivot_measure_row:nth-of-type(3)", ["mouseout"]);
        assert.containsNone(target, ".o_cell_hover");
    });

    QUnit.test(
        "columns are highlighted when hovering an origin (comparison mode)",
        async function (assert) {
            assert.expect(5);

            patchDate(2016, 11, 20, 1, 0, 0);

            serverData.models.partner.records[0].date = "2016-11-15";
            serverData.models.partner.records[1].date = "2016-12-17";
            serverData.models.partner.records[2].date = "2016-11-22";
            serverData.models.partner.records[3].date = "2016-11-03";

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="date" type="col"/>
                </pivot>`,
                searchViewArch: `
                <search>
                    <filter name="date_filter" date="date" domain="[]" default_period='this_month'/>
                </search>`,
                context: { search_default_date_filter: true },
            });

            await toggleComparisonMenu(target);
            await toggleMenuItem(target, "Date: Previous period");

            // hover the second origin in second group
            await triggerEvents(target, "th.o_pivot_origin_row:nth-of-type(5)", ["mouseover"]);
            assert.containsN(target, ".o_cell_hover", 3);
            for (let i = 1; i <= 3; i++) {
                assert.hasClass(
                    target.querySelector(`tbody tr:nth-of-type(${i}) td:nth-of-type(5)`),
                    "o_cell_hover"
                );
            }
            await triggerEvents(target, "th.o_pivot_origin_row:nth-of-type(5)", ["mouseout"]);
            assert.containsNone(target, ".o_cell_hover");
        }
    );

    QUnit.test('pivot view with disable_linking="True"', async function (assert) {
        const fakeActionService = {
            start() {
                return {
                    doAction() {
                        throw new Error("should not execute an action");
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot disable_linking="True">
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        assert.doesNotHaveClass(target.querySelector("table"), "o_enable_linking");
        assert.containsOnce(target, ".o_pivot_cell_value");
        await click(target.querySelector(".o_pivot_cell_value")); // should not trigger a do_action
    });

    QUnit.test('clicking on the "Total" cell with time range activated', async function (assert) {
        assert.expect(2);

        patchDate(2016, 11, 20, 1, 0, 0);

        const fakeActionService = {
            start() {
                return {
                    doAction(action) {
                        assert.deepEqual(
                            action.domain,
                            ["&", ["date", ">=", "2016-12-01"], ["date", "<=", "2016-12-31"]],
                            "should trigger do_action with the correct action domain"
                        );
                        return Promise.resolve(true);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: "<pivot/>",
            searchViewArch: `
                <search>
                    <filter name="date_filter" date="date" domain="[]" default_period='this_month'/>
                </search>`,
            context: { search_default_date_filter: true },
        });

        assert.hasClass(
            target.querySelector("table"),
            "o_enable_linking",
            "root node should have classname 'o_enable_linking'"
        );
        await click(target.querySelector(".o_pivot_cell_value"));
    });

    QUnit.test(
        'clicking on a fake cell value ("empty group") in comparison mode',
        async function (assert) {
            assert.expect(3);

            patchDate(2016, 11, 20, 1, 0, 0);

            serverData.models.partner.records[0].date = "2016-11-15";
            serverData.models.partner.records[1].date = "2016-11-17";
            serverData.models.partner.records[2].date = "2016-11-22";
            serverData.models.partner.records[3].date = "2016-11-03";

            const expectedDomains = [
                ["&", ["date", ">=", "2016-12-01"], ["date", "<=", "2016-12-31"]],
                [[0, "=", 1]],
            ];
            const fakeActionService = {
                start() {
                    return {
                        doAction(action) {
                            assert.deepEqual(action.domain, expectedDomains.shift());
                            return Promise.resolve(true);
                        },
                    };
                },
            };
            serviceRegistry.add("action", fakeActionService, { force: true });

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `<pivot><field name="product_id" type="row"/></pivot>`,
                searchViewArch: `
                    <search>
                        <filter name="date_filter" date="date" domain="[]" default_period='this_month'/>
                    </search>`,
                context: { search_default_date_filter: true },
            });

            await toggleComparisonMenu(target);
            await toggleMenuItem(target, "Date: Previous period");

            assert.hasClass(target.querySelector("table"), "o_enable_linking");
            // here we click on the group corresponding to Total/Total/This Month
            target.querySelectorAll(".o_pivot_cell_value")[1].click(); // should trigger a do_action with appropriate domain
            // here we click on the group corresponding to xphone/Total/This Month
            target.querySelectorAll(".o_pivot_cell_value")[4].click(); // should trigger a do_action with appropriate domain
        }
    );

    QUnit.test("pivot view grouped by date field", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    const wrongFields = args.kwargs.fields.filter((field) => {
                        return !(field.split(":")[0] in serverData.models.partner.fields);
                    });
                    assert.ok(
                        !wrongFields.length,
                        "fields given to read_group should exist on the model"
                    );
                }
            },
        });
    });

    QUnit.test("without measures, pivot view uses __count by default", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: "<pivot></pivot>",
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["__count"],
                        "should make a read_group with no valid fields"
                    );
                }
            },
        });

        await click(target.querySelector(".o_cp_bottom_left .dropdown-toggle"));
        assert.containsOnce(target, ".o_cp_bottom_left .dropdown-menu .dropdown-item");
        const measure = target.querySelector(".o_cp_bottom_left .dropdown-menu .dropdown-item");
        assert.strictEqual(measure.innerText, "Count");
        assert.hasClass(measure, "selected", "The count measure should be selected");
    });

    QUnit.test("pivot view can be reloaded", async function (assert) {
        let readGroupCount = 0;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: "<pivot></pivot>",
            searchViewArch: `
                <search>
                    <filter name="some_filter" string="Some Filter" domain="[('foo', '>', 10)]"/>
                </search>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    readGroupCount++;
                }
            },
        });

        assert.containsOnce(
            target,
            "td.o_pivot_cell_value:contains(4)",
            "should contain a pivot cell with the number of all records"
        );
        assert.strictEqual(readGroupCount, 1, "should have done 1 rpc");

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Some Filter");
        assert.containsOnce(
            target,
            "td.o_pivot_cell_value:contains(2)",
            "should contain a pivot cell with the number of remaining records"
        );
        assert.strictEqual(readGroupCount, 2, "should have done 2 rpcs");
    });

    QUnit.test("pivot view grouped by many2one field", async function (assert) {
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        assert.containsOnce(target, ".o_pivot_header_cell_opened", "should have one opened header");
        assert.containsOnce(
            target,
            ".o_pivot_header_cell_closed:contains(xphone)",
            "should display one header with 'xphone'"
        );
        assert.containsOnce(
            target,
            ".o_pivot_header_cell_closed:contains(xpad)",
            "should display one header with 'xpad'"
        );
    });

    QUnit.test("basic folding/unfolding", async function (assert) {
        assert.expect(7);

        let rpcCount = 0;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    rpcCount++;
                }
            },
        });
        assert.containsN(
            target,
            "tbody tr",
            3,
            "should have 3 rows: 1 for the opened header, and 2 for data"
        );

        // click on the opened header to close it
        await click(target, ".o_pivot_header_cell_opened");

        assert.containsOnce(target, "tbody tr", "should have 1 row");

        // click on closed header to open dropdown
        await click(target, "tbody .o_pivot_header_cell_closed");
        assert.containsOnce(target, ".o_pivot .dropdown-menu");
        assert.strictEqual(
            target.querySelector(".o_pivot .dropdown-menu").innerText.replace(/\s/g, ""),
            "CompanyTypeCustomerDateOtherProductProductbarAddCustomGroup"
        );

        // open the Date sub dropdown
        await mouseEnter(target, ".o_pivot .dropdown-menu .dropdown-toggle.o_menu_item");
        assert.strictEqual(
            target
                .querySelector(".o_pivot .dropdown-menu .dropdown-menu")
                .innerText.replace(/\s/g, ""),
            "YearQuarterMonthWeekDay"
        );

        await click(
            target.querySelectorAll(".o_pivot .dropdown-menu .dropdown-menu .dropdown-item")[2]
        );

        assert.containsN(target, "tbody tr", 4, "should have 4 rows: one for header, 3 for data");
        assert.strictEqual(
            rpcCount,
            3,
            "should have done 3 rpcs (initial load) + open header with different groupbys"
        );
    });

    QUnit.test("more folding/unfolding", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        // open dropdown to zoom into first row
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        // click on date by day
        await mouseEnter(target.querySelector("tbody .dropdown-menu .dropdown-toggle"));
        await click(target.querySelector("tbody .dropdown-menu .dropdown-menu span:nth-child(5)"));

        // open dropdown to zoom into second row
        await click(target.querySelectorAll("tbody th.o_pivot_header_cell_closed")[1]);

        assert.containsN(
            target,
            "tbody tr",
            7,
            "should have 7 rows (1 for total, 1 for xphone, 1 for xpad, 4 for data)"
        );
    });

    QUnit.test("fold and unfold header group", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        assert.containsN(target, "thead tr", 3);

        // fold opened col group
        await click(target.querySelector("thead .o_pivot_header_cell_opened"));
        assert.containsN(target, "thead tr", 2);

        // unfold it
        await click(target.querySelector("thead .o_pivot_header_cell_closed"));
        await click(target.querySelector(".dropdown-menu span:nth-child(5)"));
        assert.containsN(target, "thead tr", 3);
    });

    QUnit.test("unfold second header group", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        assert.containsN(target, "thead tr", 3);
        let values = ["12", "20", "32"];
        assert.strictEqual(getCurrentValues(target), values.join(","));

        // unfold it
        await click(target.querySelector("thead .o_pivot_header_cell_closed:last-child"));
        await click(target.querySelector(".dropdown-menu span:nth-child(1)"));
        assert.containsN(target, "thead tr", 4);
        values = ["12", "17", "3", "32"];
        assert.strictEqual(getCurrentValues(target), values.join(","));
    });

    QUnit.test(
        "pivot renders group dropdown same as search groupby dropdown if group bys are specified in search arch",
        async function (assert) {
            assert.expect(6);

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
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
            await toggleGroupByMenu(target);
            assert.containsN(
                target,
                ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_menu_item",
                3,
                "should have 3 dropdown items in searchview groupby"
            );
            assert.containsOnce(
                target,
                ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_add_custom_group_menu",
                "should have custom group generator in searchview groupby"
            );

            // click on closed header to open dropdown
            await click(target, "tbody tr:last-child .o_pivot_header_cell_closed");
            assert.containsN(
                target,
                ".dropdown-menu > .dropdown-item",
                3,
                "should have 3 dropdown items same as searchview groupby"
            );
            assert.containsOnce(
                target,
                ".dropdown-menu .o_add_custom_group_menu",
                "should have custom group generator same as searchview groupby"
            );
            // check custom groupby selection has groupable fields only
            await mouseEnter(target, ".dropdown-menu .o_add_custom_group_menu .dropdown-toggle");
            assert.containsN(
                target,
                ".dropdown-menu .o_add_custom_group_menu .dropdown-menu option",
                6,
                "should have 6 fields in custom groupby"
            );
            const optionDescriptions = [
                ...target.querySelectorAll(
                    ".dropdown-menu .o_add_custom_group_menu .dropdown-menu option"
                ),
            ].map((option) => option.innerText.trim());
            assert.deepEqual(
                optionDescriptions,
                ["Company Type", "Customer", "Date", "Other Product", "Product", "bar"],
                "should only have groupable fields in custom groupby"
            );
        }
    );

    QUnit.test("pivot group dropdown sync with search groupby dropdown", async function (assert) {
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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
        await toggleGroupByMenu(target);
        assert.containsN(
            target,
            ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_menu_item",
            2,
            "should have 2 dropdown items in searchview groupby"
        );

        // click on closed header to open dropdown
        await click(target, "tbody tr:last-child .o_pivot_header_cell_closed");
        assert.containsN(
            target,
            ".dropdown-menu .o_menu_item",
            2,
            "should have 2 dropdown items in pivot groupby"
        );

        // add a custom group in searchview groupby
        await toggleGroupByMenu(target);
        await toggleAddCustomGroup(target);
        await applyGroup(target);
        assert.containsN(
            target,
            ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_menu_item",
            3,
            "should have 3 dropdown items in searchview groupby now"
        );
        await click(target, "tbody tr:last-child .o_pivot_header_cell_closed");
        assert.containsN(
            target,
            ".dropdown-menu .o_menu_item",
            2,
            "should still have 2 dropdown items in pivot groupby"
        );

        // add a custom group in pivot groupby
        await mouseEnter(target, ".dropdown-menu .o_add_custom_group_menu .dropdown-toggle");
        target.querySelector(".dropdown-menu .o_add_custom_group_menu select").value = "date";
        await triggerEvent(target, ".dropdown-menu .o_add_custom_group_menu select", "change");
        await click(target, ".dropdown-menu .o_add_custom_group_menu .dropdown-menu .btn");
        // click on closed header to open groupby selection dropdown
        await click(target, "tbody tr:last-child .o_pivot_header_cell_closed");
        assert.containsN(
            target,
            ".dropdown-menu .o_menu_item",
            3,
            "should have 3 dropdown items in pivot groupby dropdown"
        );

        // applying custom groupby in pivot groupby dropdown will not update search dropdown
        await toggleGroupByMenu(target);
        assert.containsN(
            target,
            ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_menu_item",
            3,
            "should still have 3 dropdown items in searchview groupby dropdown"
        );
    });

    QUnit.test(
        "pivot groupby dropdown renders custom search at the end with separator",
        async function (assert) {
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
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
            await toggleGroupByMenu(target);
            assert.containsN(
                target,
                ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_menu_item",
                2,
                "should have 2 dropdown items in searchview groupby"
            );
            await toggleAddCustomGroup(target);
            await applyGroup(target);
            assert.containsN(
                target,
                ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_menu_item",
                3,
                "should have 3 dropdown items in searchview groupby now"
            );

            // click on closed header to open dropdown
            await click(target.querySelectorAll("tbody .o_pivot_header_cell_closed")[1]);
            let items = target.querySelectorAll(".o_menu_item");
            assert.deepEqual(
                [...items].map((it) => it.innerText),
                ["bar", "product"]
            );
            assert.containsOnce(
                target,
                "tbody .dropdown-menu .dropdown-divider",
                "pivot groupby menu should only have one separator"
            );
            assert.hasClass(
                items[items.length - 1].nextElementSibling,
                "dropdown-divider",
                "pivot groupby menu separator is placed after all menu items"
            );

            // add a custom group in pivot groupby
            await mouseEnter(target, ".dropdown-menu .o_add_custom_group_menu .dropdown-toggle");
            target.querySelector(".o_add_custom_group_menu select").value = "customer";
            await triggerEvent(target, ".dropdown-menu .o_add_custom_group_menu select", "change");
            await click(target, ".dropdown-menu .o_add_custom_group_menu .dropdown-menu .btn");

            await click(target.querySelectorAll("tbody .o_pivot_header_cell_closed")[1]);
            items = target.querySelectorAll(".o_menu_item");
            assert.deepEqual(
                [...items].map((it) => it.innerText),
                ["bar", "product", "Customer"]
            );
            assert.containsN(
                target,
                "tbody .dropdown-menu .dropdown-divider",
                2,
                "pivot groupby menu should now have two separators"
            );
            assert.hasClass(
                items[items.length - 1].previousElementSibling,
                "dropdown-divider",
                "last pivot groupby menu item is placed after a separator"
            );
            assert.hasClass(
                items[items.length - 1].nextElementSibling,
                "dropdown-divider",
                "a pivot groupby menu separator is placed after all menu items"
            );
        }
    );

    QUnit.test(
        "pivot custom groupby: grouping on date field use default interval month",
        async function (assert) {
            assert.expect(1);

            let checkReadGroup = false;
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="foo" type="measure"/>
                    </pivot>`,
                searchViewArch: `
                    <search>
                        <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
                    </search>`,
                mockRPC(route, args) {
                    if (args.method === "read_group" && checkReadGroup) {
                        assert.deepEqual(
                            args.kwargs.groupby,
                            ["date:month"],
                            "should use default month as an interval in read_group"
                        );
                        checkReadGroup = false;
                    }
                },
            });

            // click on closed header to open dropdown and apply groupby on date field
            await click(target.querySelector("thead .o_pivot_header_cell_closed"));
            await mouseEnter(
                target.querySelector(
                    "thead .dropdown-menu .o_add_custom_group_menu .dropdown-toggle "
                )
            );

            checkReadGroup = true;
            const select = target.querySelector(".o_add_custom_group_menu select");
            select.value = "date";
            select.dispatchEvent(new Event("change"));
            await click(target.querySelector(".o_add_custom_group_menu .btn-primary"));
        }
    );

    QUnit.test("pivot view without group by specified in search arch", async function (assert) {
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        // open group by dropdown
        await toggleGroupByMenu(target);
        assert.containsNone(
            target,
            ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_menu_item",
            "should not have any dropdown item in searchview groupby"
        );
        assert.containsOnce(
            target,
            ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_add_custom_group_menu",
            "should have add custom group item in searchview groupby"
        );
        // click on closed header to open dropdown
        await click(target.querySelectorAll("tbody .o_pivot_header_cell_closed")[1]);
        assert.containsN(
            target,
            "tbody .dropdown-menu .o_menu_item",
            6,
            "should have 6 dropdown items i.e. all groupable fields available"
        );
        assert.containsOnce(
            target,
            ".dropdown-menu .o_add_custom_group_menu",
            "should have custom group generator in groupby dropdown"
        );
    });

    QUnit.test(
        "pivot view do not show custom group selection if there are no groupable fields",
        async function (assert) {
            assert.expect(4);

            for (const fieldName of [
                "bar",
                "company_type",
                "customer",
                "date",
                "other_product_id",
            ]) {
                delete serverData.models.partner.fields[fieldName];
            }

            // Keep product_id but make it ungroupable
            delete serverData.models.partner.fields.product_id.sortable;
            delete serverData.models.partner.fields.product_id.store;

            serverData.models.partner.records = [
                {
                    id: 1,
                    foo: 12,
                    product_id: 37,
                    computed_field: 19,
                },
            ];

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
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
            await toggleGroupByMenu(target);
            assert.containsOnce(
                target,
                ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_menu_item",
                "should have 1 dropdown item in searchview groupby"
            );
            assert.containsNone(
                target,
                ".o_control_panel .o_cp_bottom_right .dropdown-menu .o_add_custom_group_menu",
                "should not have custom group generator in searchview groupby"
            );

            // click on closed header to open dropdown
            await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
            assert.containsOnce(
                target,
                "tbody .dropdown-menu .dropdown-item",
                "should have 1 dropdown items"
            );
            assert.containsNone(
                target,
                ".dropdown-menu .o_add_custom_group_menu",
                "should not have custom group generator in groupby dropdown"
            );
        }
    );

    QUnit.test(
        "pivot custom groupby: adding a custom group close the pivot groupby menu",
        async function (assert) {
            assert.expect(3);

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
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

            // click on closed header to open dropdown
            await click(target.querySelector("thead .o_pivot_header_cell_closed"));
            assert.containsOnce(target, "thead .dropdown-menu .o_add_custom_group_menu");
            await mouseEnter(
                target.querySelector(
                    "thead .dropdown-menu .o_add_custom_group_menu .dropdown-toggle"
                )
            );
            assert.containsOnce(
                target,
                "thead .dropdown-menu .o_add_custom_group_menu .dropdown-menu"
            );

            // click on apply button should close dropdown
            await click(
                target.querySelector(
                    "thead .dropdown-menu .o_add_custom_group_menu .dropdown-menu .btn-primary"
                )
            );
            assert.containsNone(target, "thead .dropdown-menu");
        }
    );

    QUnit.test("can toggle extra measure", async function (assert) {
        let rpcCount = 0;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            mockRPC() {
                rpcCount++;
            },
        });

        rpcCount = 0;
        assert.containsN(
            target,
            ".o_pivot_cell_value",
            3,
            "should have 3 cells: 1 for the open header, and 2 for data"
        );

        await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));
        assert.doesNotHaveClass(
            $(target).find(".dropdown-item:contains(Count)"),
            "selected",
            "the __count measure should not be selected"
        );
        await click($(target).find(".o_cp_bottom_left .dropdown-item:contains(Count)")[0]);

        assert.hasClass(
            $(target).find(".o_cp_bottom_left .dropdown-item:contains(Count)"),
            "selected",
            "the __count measure should be selected"
        );
        assert.containsN(
            target,
            ".o_pivot_cell_value",
            6,
            "should have 6 cells: 2 for the open header, and 4 for data"
        );
        assert.strictEqual(rpcCount, 2, "should have done 2 rpcs to reload data");

        await click($(target).find(".o_cp_bottom_left .dropdown-item:contains(Count)")[0]);

        assert.doesNotHaveClass(
            $(target).find(".dropdown-item:contains(Count)")[0],
            "selected",
            "the __count measure should not be selected"
        );
        assert.containsN(
            target,
            ".o_pivot_cell_value",
            3,
            "should have 3 cells: 1 for the open header, and 2 for data"
        );
        assert.strictEqual(rpcCount, 2, "should not have done any extra rpcs");
    });

    QUnit.test("no content helper when no active measure", async function (assert) {
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `<pivot/>`,
        });

        assert.containsNone(target, ".o_view_nocontent");
        assert.containsOnce(target, "table");

        await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));
        await click($(target).find(".o_cp_bottom_left .dropdown-item:contains(Count)")[0]);

        assert.containsOnce(target, ".o_view_nocontent");
        assert.containsNone(target, "table");
    });

    QUnit.test("no content helper when no data", async function (assert) {
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `<pivot/>`,
            searchViewArch: `
                <search>
                    <filter name="some_filter" string="Some Filter" domain="[('foo', '=', 12345)]"/>
                </search>`,
        });

        assert.containsNone(target, ".o_view_nocontent");
        assert.containsOnce(target, "table");

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Some Filter");

        assert.containsOnce(target, ".o_view_nocontent");
        assert.containsNone(target, "table");
    });

    QUnit.test("no content helper when no data, part 2", async function (assert) {
        serverData.models.partner.records = [];

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: "<pivot/>",
        });

        assert.containsOnce(target, ".o_view_nocontent");
    });

    QUnit.test("no content helper when no data, part 3", async function (assert) {
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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

        assert.containsOnce(target, ".o_searchview .o_searchview_facet");
        assert.containsOnce(target, ".o_view_nocontent");

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Some Filter");
        assert.containsN(target, ".o_searchview .o_searchview_facet", 2);
        assert.containsOnce(target, ".o_view_nocontent");

        await toggleMenuItem(target, "Some Filter");
        assert.containsOnce(target, ".o_searchview .o_searchview_facet");
        assert.containsOnce(target, ".o_view_nocontent");

        await click(target, ".o_facet_remove");
        assert.containsNone(target, ".o_searchview .o_searchview_facet");
        assert.containsNone(target, ".o_view_nocontent");

        // tries to open a field selection menu, to make sure it was not
        // removed from the dom.
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        assert.containsOnce(target, "tbody .dropdown-menu");
    });

    QUnit.test("tries to restore previous state after domain change", async function (assert) {
        assert.expect(7);

        let rpcCount = 0;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="my_filter" string="My Filter" domain="[('foo', '=', 12345)]"/>
                </search>`,
            mockRPC() {
                rpcCount++;
            },
        });

        assert.containsN(
            target,
            ".o_pivot_cell_value",
            3,
            "should have 3 cells: 1 for the open header, and 2 for data"
        );
        assert.containsOnce(
            target,
            ".o_pivot_measure_row:contains(Foo)",
            "should have 1 row for measure Foo"
        );

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter");
        assert.containsNone(target, "table");

        rpcCount = 0;
        await removeFacet(target);

        assert.containsOnce(target, "table");
        assert.equal(rpcCount, 2, "should have reloaded data");
        assert.containsN(
            target,
            ".o_pivot_cell_value",
            3,
            "should still have 3 cells: 1 for the open header, and 2 for data"
        );
        assert.containsOnce(
            target,
            ".o_pivot_measure_row:contains(Foo)",
            "should still have 1 row for measure Foo"
        );
    });

    QUnit.test("can be grouped with the search view", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter string="Product" name="product_id" context="{'group_by':'product_id'}"/>
                </search>`,
        });

        assert.containsOnce(target, ".o_pivot_cell_value", "should have only 1 cell");
        assert.containsOnce(target, "tbody tr", "should have 1 rows");

        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Product");

        assert.containsN(target, ".o_pivot_cell_value", 3, "should have 3 cells");
        assert.containsN(target, "tbody tr", 3, "should have 3 rows");
    });

    QUnit.test("can sort data in a column by clicking on header", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                    <field name="product_id" type="row"/>
                </pivot>`,
        });

        let values = ["32", "12", "20"];
        assert.strictEqual(
            getCurrentValues(target),
            values.join(","),
            "should have proper values in cells (total, result 1, result 2)"
        );

        await click(target.querySelector("th.o_pivot_measure_row"));

        values = ["32", "12", "20"];
        assert.strictEqual(
            getCurrentValues(target),
            values.join(","),
            "should have proper values in cells (total, result 1, result 2)"
        );

        await click(target.querySelector("th.o_pivot_measure_row"));

        values = ["32", "20", "12"];
        assert.strictEqual(
            getCurrentValues(target),
            values.join(","),
            "should have proper values in cells (total, result 1, result 2)"
        );
    });

    QUnit.test("can expand all rows", async function (assert) {
        assert.expect(7);

        let nbReadGroups = 0;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    nbReadGroups++;
                }
            },
        });

        assert.strictEqual(nbReadGroups, 2, "should have done 2 read_group RPCS");
        assert.strictEqual(
            getCurrentValues(target),
            "32,12,20",
            "should have proper values in cells (total, result 1, result 2)"
        );

        // expand on date:days, product
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "Month");
        nbReadGroups = 0;
        await toggleMenuItem(target, "Product");

        assert.strictEqual(nbReadGroups, 3, "should have done 3 read_group RPCS");
        assert.containsN(
            target,
            "tbody tr",
            8,
            "should have 7 rows (total + 3 for December and 2 for October and April)"
        );

        // collapse the first two rows
        await click(target.querySelectorAll("tbody .o_pivot_header_cell_opened")[2]);
        await click(target.querySelectorAll("tbody .o_pivot_header_cell_opened")[1]);

        assert.containsN(target, "tbody tr", 6, "should have 6 rows now");

        // expand all
        nbReadGroups = 0;
        await click(target.querySelector(".o_pivot_expand_button"));

        assert.strictEqual(nbReadGroups, 3, "should have done 3 read_group RPCS");
        assert.containsN(target, "tbody tr", 8, "should have 8 rows again");
    });

    QUnit.test("expand all with a delay", async function (assert) {
        assert.expect(4);

        let def;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    return Promise.resolve(def);
                }
            },
        });

        // expand on date:days, product
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "Month");
        await toggleMenuItem(target, "Product");
        assert.containsN(
            target,
            "tbody tr",
            8,
            "should have 7 rows (total + 3 for December and 2 for October and April)"
        );

        // collapse the first two rows
        await click(target.querySelectorAll("tbody .o_pivot_header_cell_opened")[2]);
        await click(target.querySelectorAll("tbody .o_pivot_header_cell_opened")[1]);

        assert.containsN(target, "tbody tr", 6, "should have 6 rows now");

        // expand all
        def = makeDeferred();
        await click(target.querySelector(".o_pivot_expand_button"));
        assert.containsN(target, "tbody tr", 6, "should have 6 rows now");
        def.resolve();
        await nextTick();
        assert.containsN(target, "tbody tr", 8, "should have 8 rows again");
    });

    QUnit.test("can download a file", async function (assert) {
        assert.expect(1);

        mockDownload(({ url }) => {
            assert.strictEqual(url, "/web/pivot/export_xlsx");
            return Promise.resolve();
        });

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        await click(target.querySelector(".o_pivot_download"));
    });

    QUnit.test(
        "download a file with single measure, measure row displayed in table",
        async function (assert) {
            assert.expect(2);

            mockDownload(({ url, data }) => {
                data = JSON.parse(data.data);
                assert.strictEqual(url, "/web/pivot/export_xlsx");
                assert.strictEqual(
                    data.measure_headers.length,
                    4,
                    "should have measure_headers in data"
                );
                return Promise.resolve();
            });

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot>
                        <field name="date" interval="month" type="col"/>
                        <field name="foo" type="measure"/>
                    </pivot>`,
            });

            await click(target.querySelector(".o_pivot_download"));
        }
    );

    QUnit.test("download button is disabled when there is no data", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records = [];

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        assert.ok(
            target.querySelector(".o_pivot_download").disabled,
            "download button should be disabled"
        );
    });

    QUnit.test("correctly save measures and groupbys to favorite", async function (assert) {
        assert.expect(3);

        let expectedContext;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            mockRPC(route, args) {
                if (args.method === "create_or_replace") {
                    assert.deepEqual(args.args[0].context, expectedContext);
                    return true;
                }
            },
        });

        expectedContext = {
            group_by: [],
            pivot_column_groupby: ["date:day"],
            pivot_measures: ["foo"],
            pivot_row_groupby: [],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "Fav1");
        await saveFavorite(target);

        // expand header on field customer
        await click(target.querySelectorAll("thead .o_pivot_header_cell_closed")[1]);
        await click(target.querySelectorAll("thead .dropdown-menu .dropdown-item")[1]);
        expectedContext = {
            group_by: [],
            pivot_column_groupby: ["date:day", "customer"],
            pivot_measures: ["foo"],
            pivot_row_groupby: [],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "Fav2");
        await saveFavorite(target);

        // expand row on field product_id
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("tbody .dropdown-menu .dropdown-item")[4]);
        expectedContext = {
            group_by: [],
            pivot_column_groupby: ["date:day", "customer"],
            pivot_measures: ["foo"],
            pivot_row_groupby: ["product_id"],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "Fav3");
        await saveFavorite(target);
    });

    QUnit.test("correctly remove pivot_ keys from the context", async function (assert) {
        assert.expect(5);

        // in this test, we use "foo" as a measure
        serverData.models.partner.fields.foo.store = true;
        serverData.models.partner.fields.amount = {
            string: "Amount",
            type: "float",
            group_operator: "sum",
        };

        let expectedContext;

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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
            mockRPC(route, args) {
                if (args.method === "create_or_replace") {
                    assert.deepEqual(args.args[0].context, expectedContext);
                    return true;
                }
            },
        });

        // Unload the filter
        await removeFacet(target); // remove previous favorite
        expectedContext = {
            group_by: [],
            pivot_column_groupby: ["customer"],
            pivot_measures: ["foo"],
            pivot_row_groupby: ["product_id"],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "1");
        await saveFavorite(target);

        // Let's get rid of the rows groupBy
        await click(target, "tbody .o_pivot_header_cell_opened");
        expectedContext = {
            group_by: [],
            pivot_column_groupby: ["customer"],
            pivot_measures: ["foo"],
            pivot_row_groupby: [],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "2");
        await saveFavorite(target);

        // And now, get rid of both col and row groupby
        //await click(target, "tbody .o_pivot_header_cell_opened"); //It was already removed
        await click(target, "thead .o_pivot_header_cell_opened");
        expectedContext = {
            group_by: [],
            pivot_column_groupby: [],
            pivot_measures: ["foo"],
            pivot_row_groupby: [],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "3");
        await saveFavorite(target);

        // Group row by product_id
        await click(target, "tbody .o_pivot_header_cell_closed");
        await click(target, ".dropdown-menu span:nth-child(5)");
        expectedContext = {
            group_by: [],
            pivot_column_groupby: [],
            pivot_measures: ["foo"],
            pivot_row_groupby: ["product_id"],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "4");
        await saveFavorite(target);

        // Group column by customer
        await click(target, "thead .o_pivot_header_cell_closed");
        await click(target, ".dropdown-menu span:nth-child(2)");
        expectedContext = {
            group_by: [],
            pivot_column_groupby: ["customer"],
            pivot_measures: ["foo"],
            pivot_row_groupby: ["product_id"],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "5");
        await saveFavorite(target);
    });

    QUnit.test("Apply two groupby, and remove facet", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                    <pivot>
                        <field name="customer" type="row"/>
                    </pivot>`,
            "partner,false,search": `
                    <search>
                        <filter name="group_by_product" string="Product" domain="[]" context="{'group_by': 'product_id'}"/>
                        <filter name="group_by_bar" string="Bar" domain="[]" context="{'group_by': 'bar'}"/>
                    </search>`,
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
        });

        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "First"
        );

        // Apply both groupbys
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Product");
        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "xphone"
        );

        await toggleMenuItem(target, "Bar");
        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "Yes"
        );

        // remove filter
        await removeFacet(target);

        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "Yes"
        );
    });

    QUnit.test("Add a group by on the CP when a favorite already exists", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                    <pivot>
                    </pivot>`,
            "partner,false,search": `
                    <search>
                        <filter name="groubybar" string="Bar" domain="[]" context="{'group_by': 'bar'}"/>
                    </search>`,
        };

        serverData.models.partner.filters = [
            {
                context: "{'pivot_row_groupby': ['date']}",
                domain: "[]",
                id: 7,
                is_default: true,
                name: "My favorite",
                sort: "[]",
                user_id: [2, "Mitchell Admin"],
            },
        ];

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
        });

        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "April 2016"
        );

        // Apply BAR groupbys
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Bar");
        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "No"
        );

        // remove groupBy
        await toggleMenuItem(target, "Bar");
        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "April 2016"
        );

        // remove all facets
        await removeFacet(target);

        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "April 2016"
        );
    });

    QUnit.skip("Removing or adding filter shouldn't modify the row group", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                    <pivot>
                        <field name="customer" type="row"/>
                    </pivot>`,
            "partner,false,search": `
                    <search>
                        <filter name="bayou" string="Bayou" domain="[('foo','=', 12)]"/>
                    </search>`,
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
            context: { search_default_bayou: 1, group_by: ["company_type"] },
        });

        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "Company"
        );

        // Let's get rid of the rows groupBy
        await click(target, "tbody .o_pivot_header_cell_opened");

        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "Total"
        );

        // Group row by product_id
        await click(target, "tbody .o_pivot_header_cell_closed");
        await click(target, ".dropdown-menu span:nth-child(5)");

        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "xphone"
        );

        // remove filter
        await removeFacet(target);

        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "xphone"
        );
    });

    QUnit.test(
        "Adding a Favorite at anytime should modify the row/column groupby",
        async function (assert) {
            serverData.views = {
                "partner,false,pivot": `
                    <pivot>
                        <field name="customer" type="row"/>
                        <field name="date" interval="month" type="col" />
                    </pivot>`,
                "partner,false,search": "<search/>",
            };
            serverData.models["partner"].filters = [
                {
                    user_id: [2, "Mitchell Admin"],
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

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, {
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "pivot"]],
            });

            assert.strictEqual(
                target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
                "First"
            );

            assert.strictEqual(
                target.querySelector("thead .o_pivot_header_cell_closed").textContent,
                "April 2016"
            );

            // activate the unique existing favorite
            await toggleFavoriteMenu(target);
            await toggleMenuItem(target, 0);

            assert.strictEqual(
                target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
                "xphone"
            );

            assert.strictEqual(
                target.querySelector("thead .o_pivot_header_cell_closed").textContent,
                "No"
            );

            // desactivate the unique existing favorite
            await toggleMenuItem(target, 0);

            assert.strictEqual(
                target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
                "xphone"
            );

            assert.strictEqual(
                target.querySelector("thead .o_pivot_header_cell_closed").textContent,
                "No"
            );

            // Let's get rid of the rows and columns groupBy
            await click(target, "tbody .o_pivot_header_cell_opened");
            await click(target, "thead .o_pivot_header_cell_opened");

            assert.strictEqual(
                target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
                "Total"
            );

            assert.strictEqual(
                target.querySelector("thead .o_pivot_header_cell_closed").textContent,
                "Total"
            );

            // activate AGAIN the unique existing favorite
            await toggleFavoriteMenu(target);
            await toggleMenuItem(target, 0);

            assert.strictEqual(
                target.querySelector("tbody .o_pivot_header_cell_closed").textContent,
                "xphone"
            );

            assert.strictEqual(
                target.querySelector("thead .o_pivot_header_cell_closed").textContent,
                "No"
            );
        }
    );

    QUnit.test("Unload Filter, reset display, load another filter", async function (assert) {
        assert.expect(18);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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
        assert.strictEqual(
            $(target).find("thead .o_pivot_header_cell_opened").length,
            1,
            "The column should be grouped"
        );
        assert.strictEqual(
            $(target).find('thead tr:contains("First")').length,
            1,
            'There should be a column "First"'
        );
        assert.strictEqual(
            $(target).find('thead tr:contains("Second")').length,
            1,
            'There should be a column "Second"'
        );

        // Check Rows
        assert.strictEqual(
            $(target).find("tbody .o_pivot_header_cell_opened").length,
            1,
            "The row should be grouped"
        );
        assert.strictEqual(
            $(target).find('tbody tr:contains("xphone")').length,
            1,
            'There should be a row "xphone"'
        );
        assert.strictEqual(
            $(target).find('tbody tr:contains("xpad")').length,
            1,
            'There should be a row "xpad"'
        );

        // Equivalent to unload the filter
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My fake favorite");
        // collapse all headers
        await click(target, ".o_pivot_header_cell_opened:first-child");
        await click(target, ".o_pivot_header_cell_opened");

        // Check Columns
        assert.strictEqual(
            $(target).find("thead .o_pivot_header_cell_closed").length,
            1,
            "The column should not be grouped"
        );
        assert.strictEqual(
            $(target).find('thead tr:contains("First")').length,
            0,
            'There should not be a column "First"'
        );
        assert.strictEqual(
            $(target).find('thead tr:contains("Second")').length,
            0,
            'There should not be a column "Second"'
        );

        // Check Rows
        assert.strictEqual(
            $(target).find("tbody .o_pivot_header_cell_closed").length,
            1,
            "The row should not be grouped"
        );
        assert.strictEqual(
            $(target).find('tbody tr:contains("xphone")').length,
            0,
            'There should not be a row "xphone"'
        );
        assert.strictEqual(
            $(target).find('tbody tr:contains("xpad")').length,
            0,
            'There should not be a row "xpad"'
        );

        // Equivalent to load another filter
        await removeFacet(target); // remove previously saved favorite
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My fake favorite 2");

        // Check Columns
        assert.strictEqual(
            $(target).find("thead .o_pivot_header_cell_opened").length,
            1,
            "The column should be grouped"
        );
        assert.strictEqual(
            $(target).find('thead tr:contains("First")').length,
            1,
            'There should be a column "First"'
        );
        assert.strictEqual(
            $(target).find('thead tr:contains("Second")').length,
            1,
            'There should be a column "Second"'
        );

        // Check Rows
        assert.strictEqual(
            $(target).find("tbody .o_pivot_header_cell_opened").length,
            1,
            "The row should be grouped"
        );
        assert.strictEqual(
            $(target).find('tbody tr:contains("xphone")').length,
            1,
            'There should be a row "xphone"'
        );
        assert.strictEqual(
            $(target).find('tbody tr:contains("xpad")').length,
            1,
            'There should be a row "xpad"'
        );
    });

    QUnit.test("Reload, group by columns, reload", async function (assert) {
        assert.expect(2);

        let expectedContext;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: "<pivot/>",
            searchViewArch: `
                <search>
                    <filter name="my_filter_1" string="My Filter 1" domain="[('product_id', '=', 37)]"/>
                    <filter name="my_filter_2" string="My Filter 2" domain="[('product_id', '=', 41)]"/>
                </search>`,
            mockRPC(route, args) {
                if (args.method === "create_or_replace") {
                    assert.deepEqual(args.args[0].context, expectedContext);
                    return true;
                }
            },
        });

        // Set a column groupby
        await click(target.querySelector("thead .o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("thead .dropdown-item")[1]);

        // Set a domain
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter 1");

        // Save to favorites and check that column groupbys were not lost
        expectedContext = {
            group_by: [],
            pivot_column_groupby: ["customer"],
            pivot_measures: ["__count"],
            pivot_row_groupby: [],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "My favorite 1");
        await saveFavorite(target);

        // Set a column groupby
        await removeFacet(target); // remove previously saved favorite
        await click(target.querySelector("thead .o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("thead .dropdown-menu .dropdown-item")[4]);

        // Set a domain
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter 2");

        expectedContext = {
            group_by: [],
            pivot_column_groupby: ["customer", "product_id"],
            pivot_measures: ["__count"],
            pivot_row_groupby: [],
        };
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "My favorite 2");
        await saveFavorite(target);
    });

    QUnit.test("folded groups remain folded at reload", async function (assert) {
        assert.expect(5);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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
        assert.strictEqual(getCurrentValues(target), values.join(","));

        // expand a col group
        await click(target.querySelectorAll("thead .o_pivot_header_cell_closed")[1]);
        await click(target.querySelectorAll("thead .dropdown-menu .dropdown-item")[1]);

        values = ["29", "2", "1", "32", "12", "12", "17", "2", "1", "20"];
        assert.strictEqual(getCurrentValues(target), values.join(","));

        // expand a row group
        await click(target.querySelectorAll("tbody .o_pivot_header_cell_closed")[1]);
        await click(target.querySelectorAll("tbody .dropdown-menu .dropdown-item")[3]);

        values = ["29", "2", "1", "32", "12", "12", "17", "2", "1", "20", "17", "2", "1", "20"];
        assert.strictEqual(getCurrentValues(target), values.join(","));

        // reload (should keep folded groups folded as col/row groupbys didn't change)
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Dummy Filter");

        assert.strictEqual(getCurrentValues(target), values.join(","));

        await click(target.querySelector(".o_pivot_expand_button"));

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
        assert.strictEqual(getCurrentValues(target), values.join(","));
    });

    QUnit.test("Empty results keep groupbys", async function (assert) {
        assert.expect(6);

        const expectedContext = {
            group_by: [],
            pivot_column_groupby: ["customer"],
            pivot_measures: ["__count"],
            pivot_row_groupby: [],
        };

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: "<pivot/>",
            searchViewArch: `
                <search>
                    <filter name="my_filter_1" string="My Filter 1" domain="[('id', '=', 0)]"/>
                    <filter name="my_filter_2" string="My Filter 2" domain="[('product_id', '=', 37)]"/>
                </search>`,
            mockRPC(route, args) {
                if (args.method === "create_or_replace") {
                    assert.deepEqual(args.args[0].context, expectedContext);
                    return true;
                }
            },
        });

        // Set a column groupby
        await click(target.querySelector("thead .o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("thead .dropdown-menu .dropdown-item")[1]);

        assert.containsOnce(target, "table");

        // Set a domain for empty results
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter 1");
        assert.containsNone(target, "table");

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "My favorite 1");
        await saveFavorite(target);

        // Set a domain for not empty results
        await removeFacet(target); // remove previously saved favorite
        assert.containsOnce(target, "table");

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter 2");
        assert.containsOnce(target, "table");

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "My favorite 2");
        await saveFavorite(target);
    });

    QUnit.test("correctly uses pivot_ keys from the context", async function (assert) {
        assert.expect(7);

        // in this test, we use "foo" as a measure
        serverData.models.partner.fields.foo.store = true;
        serverData.models.partner.fields.amount = {
            string: "Amount",
            type: "float",
            group_operator: "sum",
        };

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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

        assert.containsOnce(
            target,
            "thead .o_pivot_header_cell_opened",
            "column: should have one opened header"
        );
        assert.containsOnce(
            target,
            "thead .o_pivot_header_cell_closed:contains(First)",
            "column: should display one closed header with 'First'"
        );
        assert.containsOnce(
            target,
            "thead .o_pivot_header_cell_closed:contains(Second)",
            "column: should display one closed header with 'Second'"
        );

        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_opened",
            "row: should have one opened header"
        );
        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_closed:contains(xphone)",
            "row: should display one closed header with 'xphone'"
        );
        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_closed:contains(xpad)",
            "row: should display one closed header with 'xpad'"
        );

        assert.strictEqual(
            target.querySelector("tbody tr").querySelectorAll("td")[2].innerText,
            "32",
            "selected measure should be foo, with total 32"
        );
    });

    QUnit.test("clear table cells data after closeGroup", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: "<pivot/>",
            groupBy: ["product_id"],
        });

        await click(target.querySelector("thead .o_pivot_header_cell_closed"));
        await mouseEnter(target.querySelector("thead .dropdown-menu .dropdown-toggle"));
        await click(
            target.querySelectorAll("thead .dropdown-menu .dropdown-menu .dropdown-item")[3]
        );

        // close and reopen row groupings after changing value
        serverData.models.partner.records.find((r) => r.product_id === 37).date = "2016-10-27";

        await click(target.querySelector("tbody .o_pivot_header_cell_opened"));
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("tbody .dropdown-menu .dropdown-item")[4]);
        assert.strictEqual(target.querySelectorAll(".o_pivot_cell_value")[4].innerText, ""); // xphone December 2016

        // invert axis, and reopen column groupings
        await click(target.querySelector(".o_cp_bottom_left .o_pivot_flip_button"));
        await click(target.querySelector("thead .o_pivot_header_cell_opened"));
        await click(target.querySelector("thead .o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("thead .dropdown-menu .dropdown-item")[4]);
        assert.strictEqual(target.querySelectorAll(".o_pivot_cell_value")[3].innerText, ""); // December 2016 xphone
    });

    QUnit.test("correctly group data after flip (1)", async function (assert) {
        assert.expect(4);

        serverData.views = {
            "partner,false,pivot": "<pivot/>",
            "partner,false,search": `<search><filter name="bayou" string="Bayou" domain="[(1,'=',1)]"/></search>`,
            "partner,false,list": '<tree><field name="foo"/></tree>',
            "partner,false,form": '<form><field name="foo"/></form>',
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
            context: { group_by: ["product_id"] },
        });

        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((e) => e.innerText),
            ["Total", "xphone", "xpad"]
        );

        // flip axis
        await click(target.querySelector(".o_pivot_flip_button"));

        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((e) => e.innerText),
            ["Total"]
        );

        // select filter "Bayou" in control panel
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Bayou");

        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((e) => e.innerText),
            ["Total", "xphone", "xpad"]
        );

        // close row header "Total"
        await click(target.querySelector("tbody .o_pivot_header_cell_opened"));

        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((e) => e.innerText),
            ["Total"]
        );
    });

    QUnit.test("correctly group data after flip (2)", async function (assert) {
        assert.expect(5);

        serverData.views = {
            "partner,false,pivot": "<pivot/>",
            "partner,false,search": `<search><filter name="bayou" string="Bayou" domain="[(1,'=',1)]"/></search>`,
            "partner,false,list": '<tree><field name="foo"/></tree>',
            "partner,false,form": '<form><field name="foo"/></form>',
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
            context: { group_by: ["product_id"] },
        });

        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((e) => e.innerText),
            ["Total", "xphone", "xpad"]
        );

        // select filter "Bayou" in control panel
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Bayou");

        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((e) => e.innerText),
            ["Total", "xphone", "xpad"]
        );

        // flip axis
        await click(target.querySelector(".o_pivot_flip_button"));

        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((e) => e.innerText),
            ["Total"]
        );

        // unselect filter "Bayou" in control panel
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Bayou");

        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((e) => e.innerText),
            ["Total", "xphone", "xpad"]
        );

        // close row header "Total"
        await click(target.querySelector("tbody .o_pivot_header_cell_opened"));

        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((e) => e.innerText),
            ["Total"]
        );
    });

    QUnit.test("correctly uses pivot_ keys from the context (at reload)", async function (assert) {
        assert.expect(8);

        // in this test, we use "foo" as a measure
        serverData.models.partner.fields.foo.store = true;
        serverData.models.partner.fields.amount = {
            string: "Amount",
            type: "float",
            group_operator: "sum",
        };

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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

        assert.strictEqual(
            target.querySelector("tbody tr").querySelectorAll("td.o_pivot_cell_value")[4].innerText,
            "0.00",
            "the active measure should be amount"
        );

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My fake favorite");

        assert.containsOnce(
            target,
            "thead .o_pivot_header_cell_opened",
            "column: should have one opened header"
        );
        assert.containsOnce(
            target,
            "thead .o_pivot_header_cell_closed:contains(First)",
            "column: should display one closed header with 'First'"
        );
        assert.containsOnce(
            target,
            "thead .o_pivot_header_cell_closed:contains(Second)",
            "column: should display one closed header with 'Second'"
        );

        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_opened",
            "row: should have one opened header"
        );
        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_closed:contains(xphone)",
            "row: should display one closed header with 'xphone'"
        );
        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_closed:contains(xpad)",
            "row: should display one closed header with 'xpad'"
        );

        assert.strictEqual(
            target.querySelector("tbody tr").querySelectorAll("td")[2].innerText,
            "32",
            "selected measure should be foo, with total 32"
        );
    });

    QUnit.test("correctly use group_by key from the context", async function (assert) {
        assert.expect(7);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="customer" type="col" />
                    <field name="foo" type="measure" />
                </pivot>`,
            groupBy: ["product_id"],
        });

        assert.containsOnce(
            target,
            "thead .o_pivot_header_cell_opened",
            "column: should have one opened header"
        );
        assert.containsOnce(
            target,
            "thead .o_pivot_header_cell_closed:contains(First)",
            'column: should display one closed header with "First"'
        );
        assert.containsOnce(
            target,
            "thead .o_pivot_header_cell_closed:contains(Second)",
            'column: should display one closed header with "Second"'
        );

        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_opened",
            "row: should have one opened header"
        );
        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_closed:contains(xphone)",
            'row: should display one closed header with "xphone"'
        );
        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_closed:contains(xpad)",
            'row: should display one closed header with "xpad"'
        );

        assert.strictEqual(
            target.querySelector("tbody tr").querySelectorAll("td")[2].innerText,
            "32",
            "selected measure should be foo, with total 32"
        );
    });

    QUnit.test(
        "correctly uses pivot_row_groupby key with default groupBy from the context",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.fields.amount = {
                string: "Amount",
                type: "float",
                group_operator: "sum",
            };

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
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

            assert.containsOnce(
                target,
                "thead .o_pivot_header_cell_opened",
                "column: should have one opened header"
            );
            assert.containsOnce(
                target,
                "thead .o_pivot_header_cell_closed:contains(First)",
                "column: should display one closed header with 'First'"
            );
            assert.containsOnce(
                target,
                "thead .o_pivot_header_cell_closed:contains(Second)",
                "column: should display one closed header with 'Second'"
            );

            // With pivot_row_groupby, groupBy customer should replace and eventually display product_id
            assert.containsOnce(
                target,
                "tbody .o_pivot_header_cell_opened",
                "row: should have one opened header"
            );
            assert.containsOnce(
                target,
                "tbody .o_pivot_header_cell_closed:contains(xphone)",
                "row: should display one closed header with 'xphone'"
            );
            assert.containsOnce(
                target,
                "tbody .o_pivot_header_cell_closed:contains(xpad)",
                "row: should display one closed header with 'xpad'"
            );
        }
    );

    QUnit.test("pivot still handles __count__ measure", async function (assert) {
        // for retro-compatibility reasons, the pivot view still handles
        // '__count__' measure.
        assert.expect(4);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: "<pivot></pivot>",
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["__count"],
                        "should make a read_group with field __count"
                    );
                }
            },
            context: {
                pivot_measures: ["__count__"],
            },
        });

        await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));
        assert.containsOnce(target, ".o_cp_bottom_left .dropdown-item");
        assert.strictEqual(
            target.querySelector(".o_cp_bottom_left .dropdown-item").innerText,
            "Count"
        );
        assert.hasClass(target.querySelector(".o_cp_bottom_left .dropdown-item"), "selected");
    });

    QUnit.test("not use a many2one as a measure by default", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id"/>
                    <field name="date" interval="month" type="col"/>
                </pivot>`,
        });
        await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));
        assert.containsOnce(target, ".o_cp_bottom_left .dropdown-item");
        assert.strictEqual(
            target.querySelector(".o_cp_bottom_left .dropdown-item").innerText,
            "Count"
        );
        assert.hasClass(target.querySelector(".o_cp_bottom_left .dropdown-item"), "selected");
    });

    QUnit.test("pivot view with many2one field as a measure", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="measure"/>
                    <field name="date" interval="month" type="col"/>
                </pivot>`,
        });

        assert.strictEqual(
            target.querySelector("table tbody tr").innerText.replace(/\s/g, ""),
            "Total1122",
            "should display product_id count as measure"
        );
    });

    QUnit.test("m2o as measure, drilling down into data", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="measure"/>
                </pivot>`,
        });
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        // click on date by month
        await mouseEnter(target.querySelector("tbody .dropdown-menu .dropdown-toggle"));
        await click(
            target.querySelectorAll("tbody .dropdown-menu .dropdown-menu .dropdown-item")[3]
        );

        assert.strictEqual(
            [...target.querySelectorAll(".o_pivot_cell_value")].map((c) => c.innerText).join(""),
            "2112",
            "should have loaded the proper data"
        );
    });

    QUnit.test("Row and column groupbys plus a domain", async function (assert) {
        assert.expect(3);

        const expectedContext = {
            group_by: [],
            pivot_column_groupby: ["customer"],
            pivot_measures: ["foo"],
            pivot_row_groupby: ["product_id"],
        };
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="some_filter" string="Some Filter" domain="[('product_id', '=', 41)]"/>
                </search>`,
            mockRPC(route, args) {
                if (args.method === "create_or_replace") {
                    assert.deepEqual(args.args[0].context, expectedContext);
                    return true;
                }
            },
        });

        // Set a column groupby
        await click(target.querySelector("thead .o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("thead .dropdown-item")[1]);

        // Set a Row groupby
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("tbody .dropdown-item")[4]);

        // Add a filter
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Some Filter");

        assert.containsOnce(
            target,
            "tbody .o_pivot_header_cell_closed",
            "There should be only one product line because of the domain"
        );
        assert.strictEqual(
            target.querySelector("tbody .o_pivot_header_cell_closed").innerText,
            "xpad",
            "The product should be the right one"
        );

        // Save current search to favorite
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "My favorite");
        await saveFavorite(target);
    });

    QUnit.test(
        "parallel data loading should discard all but the last one",
        async function (assert) {
            assert.expect(6);

            let def;
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot>
                        <field name="foo" type="measure"/>
                    </pivot>`,
                searchViewArch: `
                    <search>
                        <filter string="Product" name="product_id" context="{'group_by':'product_id'}"/>
                        <filter string="Customer" name="customer" context="{'group_by':'customer'}"/>
                    </search>`,
                mockRPC(route, args) {
                    if (args.method === "read_group") {
                        return Promise.resolve(def);
                    }
                },
            });

            assert.containsOnce(target, ".o_pivot_cell_value", "should have 1 cell initially");
            assert.containsOnce(target, "tbody tr", "should have 1 row initially");

            def = makeDeferred();
            await toggleGroupByMenu(target);
            await toggleMenuItem(target, "Product");
            await toggleMenuItem(target, "Customer");

            assert.containsOnce(target, ".o_pivot_cell_value", "should still have 1 cell");
            assert.containsOnce(target, "tbody tr", "should still have 1 row");

            await def.resolve();
            await nextTick();

            assert.containsN(target, ".o_pivot_cell_value", 6, "should have 6 cells");
            assert.containsN(target, "tbody tr", 6, "should have 6 rows");
        }
    );

    QUnit.test("pivot measures should be alphabetically sorted", async function (assert) {
        assert.expect(1);

        // It's important to compare capitalized and lowercased words
        // to be sure the sorting is effective with both of them
        serverData.models.partner.fields.bouh = {
            string: "bouh",
            type: "integer",
            group_operator: "sum",
        };
        serverData.models.partner.fields.modd = {
            string: "modd",
            type: "integer",
            group_operator: "sum",
        };
        serverData.models.partner.fields.zip = {
            string: "Zip",
            type: "integer",
            group_operator: "sum",
        };

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="zip" type="measure"/>
                    <field name="foo" type="measure"/>
                    <field name="bouh" type="measure"/>
                    <field name="modd" type="measure"/>
                </pivot>`,
        });

        await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));
        assert.strictEqual(
            [...target.querySelectorAll(".o_cp_bottom_left .dropdown-item")]
                .map((i) => i.innerText)
                .join(""),
            "bouhFoomoddZipCount"
        );
    });

    QUnit.test("pivot view should use default order for auto sorting", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot default_order="foo asc">
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        assert.hasClass(
            target.querySelector("thead th.o_pivot_measure_row"),
            "o_pivot_sort_order_asc"
        );
    });

    QUnit.test("pivot view can be flipped", async function (assert) {
        assert.expect(5);

        var rpcCount = 0;

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="product_id" type="row"/>
                </pivot>`,
            mockRPC() {
                rpcCount++;
            },
        });

        assert.containsN(
            target,
            "tbody tr",
            3,
            "should have 3 rows: 1 for the open header, and 2 for data"
        );
        let values = ["4", "1", "3"];
        assert.strictEqual(getCurrentValues(target), values.join());

        rpcCount = 0;
        await click(target.querySelector(".o_pivot_flip_button"));

        assert.strictEqual(rpcCount, 0, "should not have done any rpc");
        assert.containsOnce(target, "tbody tr", "should have 1 rows: 1 for the main header");

        values = ["1", "3", "4"];
        assert.strictEqual(getCurrentValues(target), values.join());
    });

    QUnit.test("rendering of pivot view with comparison", async function (assert) {
        serverData.models.partner.records[0].date = "2016-12-15";
        serverData.models.partner.records[1].date = "2016-12-17";
        serverData.models.partner.records[2].date = "2016-11-22";
        serverData.models.partner.records[3].date = "2016-11-03";

        patchDate(2016, 11, 20, 1, 0, 0);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="date_filter" date="date" domain="[]" default_period='last_year'/>
                </search>`,
            context: { search_default_date_filter: 1 },
            mockRPC(route, args) {
                if (args.method === "create_or_replace") {
                    assert.deepEqual(args.args[0].context, {
                        pivot_measures: ["__count"],
                        pivot_column_groupby: [],
                        pivot_row_groupby: ["product_id"],
                        group_by: [],
                        comparison: {
                            comparisonId: "previous_period",
                            comparisonRange: [
                                "&",
                                ["date", ">=", "2016-11-01"],
                                ["date", "<=", "2016-11-30"],
                            ],
                            comparisonRangeDescription: "November 2016",
                            fieldDescription: "Date",
                            fieldName: "date",
                            range: [
                                "&",
                                ["date", ">=", "2016-12-01"],
                                ["date", "<=", "2016-12-31"],
                            ],
                            rangeDescription: "December 2016",
                        },
                    });
                    return true;
                }
            },
        });

        // with no data
        await toggleComparisonMenu(target);
        await toggleMenuItem(target, "Date: Previous period");

        assert.containsOnce(target, "p.o_view_nocontent_empty_folder");

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "December");
        await toggleMenuItemOption(target, "Date", "2016");
        await toggleMenuItemOption(target, "Date", "2015");

        assert.containsN(
            target,
            ".o_pivot thead tr:last th",
            9,
            "last header row should contains 9 cells (3*[December 2016, November 2016, Variation]"
        );
        let values = ["19", "0", "-100%", "0", "13", "100%", "19", "13", "-31.58%"];
        assert.strictEqual(getCurrentValues(target), values.join());

        // with data, with row groupby
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("tbody .dropdown-menu .dropdown-item")[4]);
        values = [
            "19",
            "0",
            "-100%",
            "0",
            "13",
            "100%",
            "19",
            "13",
            "-31.58%",
            "19",
            "0",
            "-100%",
            "0",
            "1",
            "100%",
            "19",
            "1",
            "-94.74%",
            "0",
            "12",
            "100%",
            "0",
            "12",
            "100%",
        ];
        assert.strictEqual(getCurrentValues(target), values.join());

        await click(target.querySelector(".o_cp_bottom_left button.dropdown-toggle"));

        await click(target.querySelectorAll(".o_cp_bottom_left .dropdown-menu .dropdown-item")[0]);
        await click(target.querySelectorAll(".o_cp_bottom_left .dropdown-menu .dropdown-item")[1]);
        values = ["2,0,-100%,0,2,100%,2,2,0%,2,0,-100%,0,1,100%,2,1,-50%,0,1,100%,0,1,100%"];
        assert.strictEqual(getCurrentValues(target), values.join());

        await click(target.querySelector("thead .o_pivot_header_cell_opened"));
        values = ["2", "2", "0%", "2", "1", "-50%", "0", "1", "100%"];
        assert.strictEqual(getCurrentValues(target), values.join());

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "Fav");
        await saveFavorite(target);
    });

    QUnit.test("export data in excel with comparison", async function (assert) {
        assert.expect(12);

        serverData.models.partner.records[0].date = "2016-12-15";
        serverData.models.partner.records[1].date = "2016-12-17";
        serverData.models.partner.records[2].date = "2016-11-22";
        serverData.models.partner.records[3].date = "2016-11-03";

        patchDate(2016, 11, 20, 1, 0, 0);

        mockDownload(({ url, data }) => {
            data = JSON.parse(data.data);
            for (const l of data.col_group_headers) {
                const titles = l.map((o) => o.title);
                assert.step(JSON.stringify(titles));
            }
            const measures = data.measure_headers.map((o) => o.title);
            assert.step(JSON.stringify(measures));
            const origins = data.origin_headers.map((o) => o.title);
            assert.step(JSON.stringify(origins));
            assert.step(String(data.measure_count));
            assert.step(String(data.origin_count));
            const valuesLength = data.rows.map((o) => o.values.length);
            assert.step(JSON.stringify(valuesLength));
            assert.strictEqual(
                url,
                "/web/pivot/export_xlsx",
                "should call get_file with correct parameters"
            );
            return Promise.resolve();
        });

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="date_filter" date="date" domain="[]" default_period='antepenultimate_month'/>
                </search>`,
            context: { search_default_date_filter: 1 },
        });

        // open comparison menu
        await toggleComparisonMenu(target);
        // compare October 2016 to September 2016
        await toggleMenuItem(target, "Date: Previous period");

        // With the data above, the time ranges contain no record.
        assert.containsOnce(target, "p.o_view_nocontent_empty_folder", "there should be no data");
        // export data should be impossible since the pivot buttons
        // are deactivated (exception: the 'Measures' button).
        assert.ok(target.querySelector(".o_control_panel button.o_pivot_download").disabled);

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "December");
        await toggleMenuItemOption(target, "Date", "October");
        assert.notOk(target.querySelector(".o_control_panel button.o_pivot_download").disabled);

        // With the data above, the time ranges contain some records.
        // export data. Should execute 'get_file'
        await click(target.querySelector(".o_control_panel button.o_pivot_download"));

        assert.verifySteps([
            // col group headers
            '["Total",""]',
            '["November 2016","December 2016"]',
            // measure headers
            '["Foo","Foo","Foo"]',
            // origin headers
            '["November 2016","December 2016","Variation","November 2016","December 2016"' +
                ',"Variation","November 2016","December 2016","Variation"]',
            // number of 'measures'
            "1",
            // number of 'origins'
            "2",
            // rows values length
            "[9]",
        ]);
    });

    QUnit.test("rendering pivot view with comparison and count measure", async function (assert) {
        assert.expect(2);

        let mockMock = false;
        let nbReadGroup = 0;

        serverData.models.partner.records[0].date = "2016-12-15";
        serverData.models.partner.records[1].date = "2016-12-17";
        serverData.models.partner.records[2].date = "2016-12-22";
        serverData.models.partner.records[3].date = "2016-12-03";

        patchDate(2016, 11, 20, 1, 0, 0);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: '<pivot><field name="customer" type="row"/></pivot>',
            searchViewArch: `
                <search>
                    <filter name="date_filter" date="date" domain="[]" default_period='this_month'/>
                </search>`,
            context: { search_default_date_filter: 1 },
            mockRPC(route, args) {
                if (args.method === "read_group" && mockMock) {
                    nbReadGroup++;
                    if (nbReadGroup === 4) {
                        // this modification is necessary because mockReadGroup does not
                        // properly reflect the server response when there is no record
                        // and a groupby list of length at least one.
                        return Promise.resolve([{}]);
                    }
                }
            },
        });

        mockMock = true;

        // compare December 2016 to November 2016
        await toggleComparisonMenu(target);
        await toggleMenuItem(target, "Date: Previous period");

        const values = ["0", "4", "100%", "0", "2", "100%", "0", "2", "100%"];
        assert.strictEqual(getCurrentValues(target), values.join(","));
        assert.containsN(
            target,
            ".o_pivot_header_cell_closed",
            3,
            "there should be exactly three closed header ('Total','First', 'Second')"
        );
    });

    QUnit.test(
        "can sort a pivot view with comparison by clicking on header",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.records[0].date = "2016-12-15";
            serverData.models.partner.records[1].date = "2016-12-17";
            serverData.models.partner.records[2].date = "2016-11-22";
            serverData.models.partner.records[3].date = "2016-11-03";

            patchDate(2016, 11, 20, 1, 0, 0);
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot>
                        <field name="date" interval="day" type="row"/>
                        <field name="company_type" type="col"/>
                        <field name="foo" type="measure"/>
                    </pivot>`,
                searchViewArch: `
                    <search>
                        <filter name="date_filter" date="date" domain="[]" default_period='this_month'/>
                    </search>`,
                context: { search_default_date_filter: 1 },
            });

            // compare December 2016 to November 2016
            await toggleComparisonMenu(target);
            await toggleMenuItem(target, "Date: Previous period");

            // initial sanity check
            let values = [
                "17",
                "12",
                "-29.41%",
                "2",
                "1",
                "-50%",
                "19",
                "13",
                "-31.58%",
                "2",
                "0",
                "-100%",
                "2",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "0",
                "12",
                "100%",
                "0",
                "12",
                "100%",
                "0",
                "1",
                "100%",
                "0",
                "1",
                "100%",
            ];
            assert.strictEqual(getCurrentValues(target), values.join());

            // click on 'Foo' in column Total/Company (should sort by the period of interest, ASC)
            await click(target.querySelector(".o_pivot_measure_row"));
            values = [
                "17",
                "12",
                "-29.41%",
                "2",
                "1",
                "-50%",
                "19",
                "13",
                "-31.58%",
                "2",
                "0",
                "-100%",
                "2",
                "0",
                "-100%",
                "0",
                "12",
                "100%",
                "0",
                "12",
                "100%",
                "0",
                "1",
                "100%",
                "0",
                "1",
                "100%",
                "17",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
            ];
            assert.strictEqual(getCurrentValues(target), values.join());

            // click again on 'Foo' in column Total/Company (should sort by the period of interest, DESC)
            await click(target.querySelector(".o_pivot_measure_row"));
            values = [
                "17",
                "12",
                "-29.41%",
                "2",
                "1",
                "-50%",
                "19",
                "13",
                "-31.58%",
                "17",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "2",
                "0",
                "-100%",
                "2",
                "0",
                "-100%",
                "0",
                "12",
                "100%",
                "0",
                "12",
                "100%",
                "0",
                "1",
                "100%",
                "0",
                "1",
                "100%",
            ];
            assert.strictEqual(getCurrentValues(target), values.join());

            // click on 'This Month' in column Total/Individual/Foo
            await click(target.querySelectorAll(".o_pivot_origin_row")[3]);
            values = [
                "17",
                "12",
                "-29.41%",
                "2",
                "1",
                "-50%",
                "19",
                "13",
                "-31.58%",
                "17",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "0",
                "12",
                "100%",
                "0",
                "12",
                "100%",
                "0",
                "1",
                "100%",
                "0",
                "1",
                "100%",
                "2",
                "0",
                "-100%",
                "2",
                "0",
                "-100%",
            ];
            assert.strictEqual(getCurrentValues(target), values.join());

            // click on 'Previous Period' in column Total/Individual/Foo
            await click(target.querySelectorAll(".o_pivot_origin_row")[4]);
            values = [
                "17",
                "12",
                "-29.41%",
                "2",
                "1",
                "-50%",
                "19",
                "13",
                "-31.58%",
                "2",
                "0",
                "-100%",
                "2",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "0",
                "12",
                "100%",
                "0",
                "12",
                "100%",
                "0",
                "1",
                "100%",
                "0",
                "1",
                "100%",
            ];
            assert.strictEqual(getCurrentValues(target), values.join());

            // click on 'Variation' in column Total/Foo
            await click(target.querySelectorAll(".o_pivot_origin_row")[8]);
            values = [
                "17",
                "12",
                "-29.41%",
                "2",
                "1",
                "-50%",
                "19",
                "13",
                "-31.58%",
                "2",
                "0",
                "-100%",
                "2",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "0",
                "12",
                "100%",
                "0",
                "12",
                "100%",
                "0",
                "1",
                "100%",
                "0",
                "1",
                "100%",
            ];
            assert.strictEqual(getCurrentValues(target), values.join());
        }
    );

    QUnit.test("Click on the measure list but not on a menu item", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            // have at least a measure to have a separator in the Measures dropdown:
            //
            // Foo
            // -----
            // Count
            arch: `<pivot><field name="foo" type="measure"/></pivot>`,
        });

        assert.containsNone(target, ".o_cp_bottom_left .dropdown-menu");

        // open the "Measures" menu
        await click(target.querySelector(".o_cp_bottom_left .dropdown-toggle"));
        assert.containsOnce(target, ".o_cp_bottom_left .dropdown-menu");

        // click on the divider in the "Measures" menu does not crash
        await click(target.querySelector(".o_cp_bottom_left .dropdown-menu .dropdown-divider"));
        // the menu should still be open
        assert.containsOnce(target, ".o_cp_bottom_left .dropdown-menu");

        // click on the measure list but not on a menu item or the separator
        await click(target.querySelector(".o_cp_bottom_left .dropdown-menu"));
        // the menu should still be open
        assert.containsOnce(target, ".o_cp_bottom_left .dropdown-menu");
    });

    QUnit.test(
        "Navigation list view for a group and back with breadcrumbs",
        async function (assert) {
            assert.expect(16);

            serverData.views = {
                "partner,false,pivot": `
                    <pivot>
                        <field name="customer" type="row"/>
                    </pivot>`,
                "partner,false,search": `
                    <search>
                        <filter name="bayou" string="Bayou" domain="[('foo','=', 12)]"/>
                    </search>`,
                "partner,false,list": '<tree><field name="foo"/></tree>',
                "partner,false,form": '<form><field name="foo"/></form>',
            };

            let readGroupCount = 0;
            const mockRPC = (route, args) => {
                if (args.method === "read_group") {
                    assert.step("read_group");
                    const domain = args.kwargs.domain;
                    if ([0, 1].indexOf(readGroupCount) !== -1) {
                        assert.deepEqual(domain, [], "domain empty");
                    } else if ([2, 3, 4, 5].indexOf(readGroupCount) !== -1) {
                        assert.deepEqual(
                            domain,
                            [["foo", "=", 12]],
                            "domain conserved when back with breadcrumbs"
                        );
                    }
                    readGroupCount++;
                }
                if (args.method === "web_search_read") {
                    assert.step("search_read");
                    const domain = args.kwargs.domain;
                    assert.deepEqual(
                        domain,
                        ["&", ["customer", "=", 1], ["foo", "=", 12]],
                        "list domain is correct"
                    );
                }
            };

            const webClient = await createWebClient({ serverData, mockRPC });

            await doAction(webClient, {
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "pivot"]],
            });

            await toggleFilterMenu(target);
            await toggleMenuItem(target, 0);
            await nextTick();

            await click(target.querySelectorAll(".o_pivot_cell_value")[1]);
            await legacyExtraNextTick();

            assert.containsOnce(target, ".o_list_view");

            await click(target.querySelector(".o_control_panel ol.breadcrumb li.breadcrumb-item"));

            assert.verifySteps([
                "read_group",
                "read_group",
                "read_group",
                "read_group",
                "search_read",
                "read_group",
                "read_group",
            ]);
        }
    );

    QUnit.test(
        "Cell values are kept when flippin a pivot view in comparison mode",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].date = "2016-12-15";
            serverData.models.partner.records[1].date = "2016-12-17";
            serverData.models.partner.records[2].date = "2016-11-22";
            serverData.models.partner.records[3].date = "2016-11-03";

            patchDate(2016, 11, 20, 1, 0, 0);
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot>
                        <field name="date" interval="day" type="row"/>
                        <field name="company_type" type="col"/>
                        <field name="foo" type="measure"/>
                    </pivot>`,
                searchViewArch: `
                    <search>
                        <filter name="date_filter" date="date" domain="[]" default_period='this_month'/>
                    </search>`,
                context: { search_default_date_filter: 1 },
            });

            // compare December 2016 to November 2016
            await toggleComparisonMenu(target);
            await toggleMenuItem(target, "Date: Previous period");

            // initial sanity check
            let values = [
                "17",
                "12",
                "-29.41%",
                "2",
                "1",
                "-50%",
                "19",
                "13",
                "-31.58%",
                "2",
                "0",
                "-100%",
                "2",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "0",
                "12",
                "100%",
                "0",
                "12",
                "100%",
                "0",
                "1",
                "100%",
                "0",
                "1",
                "100%",
            ];
            assert.strictEqual(getCurrentValues(target), values.join());

            // flip table
            await click(target.querySelector(".o_pivot_flip_button"));

            values = [
                "2",
                "0",
                "-100%",
                "17",
                "0",
                "-100%",
                "0",
                "12",
                "100%",
                "0",
                "1",
                "100%",
                "19",
                "13",
                "-31.58%",
                "17",
                "0",
                "-100%",
                "0",
                "12",
                "100%",
                "17",
                "12",
                "-29.41%",
                "2",
                "0",
                "-100%",
                "0",
                "1",
                "100%",
                "2",
                "1",
                "-50%",
            ];
            assert.strictEqual(getCurrentValues(target), values.join());
        }
    );

    QUnit.test("Flip then compare, table col groupbys are kept", async function (assert) {
        assert.expect(6);

        serverData.models.partner.records[0].date = "2016-12-15";
        serverData.models.partner.records[1].date = "2016-12-17";
        serverData.models.partner.records[2].date = "2016-11-22";
        serverData.models.partner.records[3].date = "2016-11-03";

        patchDate(2016, 11, 20, 1, 0, 0);
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="date" interval="day" type="row"/>
                    <field name="company_type" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="date_filter" date="date" domain="[]" default_period='this_month'/>
                </search>`,
        });

        assert.deepEqual(
            [...target.querySelectorAll("thead th")].map((th) => th.innerText),
            ["", "Total", "", "Company", "individual", "Foo", "Foo", "Foo"],
            "The col headers should be as expected"
        );
        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((th) => th.innerText),
            ["Total", "2016-11-03", "2016-11-22", "2016-12-15", "2016-12-17"],
            "The row headers should be as expected"
        );

        // flip
        await click(target.querySelector(".o_pivot_flip_button"));

        assert.deepEqual(
            [...target.querySelectorAll("thead th")].map((th) => th.innerText),
            [
                "",
                "Total",
                "",
                "2016-11-03",
                "2016-11-22",
                "2016-12-15",
                "2016-12-17",
                "Foo",
                "Foo",
                "Foo",
                "Foo",
                "Foo",
            ],
            "The col headers should be as expected"
        );
        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((th) => th.innerText),
            ["Total", "Company", "individual"],
            "The row headers should be as expected"
        );

        // Filter on December 2016
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "December");

        // compare December 2016 to November 2016
        await toggleComparisonMenu(target);
        await toggleMenuItem(target, "Date: Previous period");

        assert.deepEqual(
            [...target.querySelectorAll("thead th")].map((th) => th.innerText),
            [
                "",
                "Total",
                "",
                "2016-11-03",
                "2016-11-22",
                "2016-12-15",
                "2016-12-17",
                "Foo",
                "Foo",
                "Foo",
                "Foo",
                "Foo",
                "November 2016",
                "December 2016",
                "Variation",
                "November 2016",
                "December 2016",
                "Variation",
                "November 2016",
                "December 2016",
                "Variation",
                "November 2016",
                "December 2016",
                "Variation",
                "November 2016",
                "December 2016",
                "Variation",
            ],
            "The col headers should be as expected"
        );
        assert.deepEqual(
            [...target.querySelectorAll("tbody th")].map((th) => th.innerText),
            ["Total", "Company", "individual"],
            "The row headers should be as expected"
        );
    });

    QUnit.test(
        "correctly compute group domain when a date field has false value",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records.forEach((r) => (r.date = false));

            patchDate(2016, 11, 20, 1, 0, 0);

            const fakeActionService = {
                start() {
                    return {
                        doAction(action) {
                            assert.deepEqual(action.domain, [["date", "=", false]]);
                            return Promise.resolve(true);
                        },
                    };
                },
            };
            serviceRegistry.add("action", fakeActionService, { force: true });

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot o_enable_linking="1">
                        <field name="date" interval="day" type="row"/>
                    </pivot>`,
            });

            await click(target.querySelectorAll(".o_value")[1]);
        }
    );
    QUnit.test(
        "Does not identify 'false' with false as keys when creating group trees",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.fields.favorite_animal = {
                string: "Favorite animal",
                type: "char",
                store: true,
            };
            serverData.models.partner.records[0].favorite_animal = "Dog";
            serverData.models.partner.records[1].favorite_animal = "false";
            serverData.models.partner.records[2].favorite_animal = "None";

            patchDate(2016, 11, 20, 1, 0, 0);
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot o_enable_linking="1">
                        <field name="favorite_animal" type="row"/>
                    </pivot>`,
            });

            assert.deepEqual(
                [...target.querySelectorAll("thead th")].map((th) => th.innerText),
                ["", "Total", "Count"],
                "The col headers should be as expected"
            );
            assert.deepEqual(
                [...target.querySelectorAll("tbody th")].map((th) => th.innerText),
                ["Total", "Dog", "None", "false", "None"],
                "The row headers should be as expected"
            );
        }
    );

    QUnit.test(
        "group bys added via control panel and expand Header do not stack",
        async function (assert) {
            assert.expect(8);

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot>
                        <field name="foo" type="measure"/>
                    </pivot>`,
            });

            assert.deepEqual(
                [...target.querySelectorAll("thead th")].map((th) => th.innerText),
                ["", "Total", "Foo"],
                "The col headers should be as expected"
            );
            assert.deepEqual(
                [...target.querySelectorAll("tbody th")].map((th) => th.innerText),
                ["Total"],
                "The row headers should be as expected"
            );

            // open group by menu and add new groupby
            await toggleGroupByMenu(target);
            await toggleAddCustomGroup(target);
            await applyGroup(target);

            assert.deepEqual(
                [...target.querySelectorAll("thead th")].map((th) => th.innerText),
                ["", "Total", "Foo"],
                "The col headers should be as expected"
            );
            assert.deepEqual(
                [...target.querySelectorAll("tbody th")].map((th) => th.innerText),
                ["Total", "Company", "individual"],
                "The row headers should be as expected"
            );

            // Set a Row groupby
            await click(target, "tbody tr:nth-child(2) .o_pivot_header_cell_closed");
            await click(target, "tbody .dropdown-menu .o_menu_item:nth-child(5)");

            assert.deepEqual(
                [...target.querySelectorAll("thead th")].map((th) => th.innerText),
                ["", "Total", "Foo"],
                "The col headers should be as expected"
            );
            assert.deepEqual(
                [...target.querySelectorAll("tbody th")].map((th) => th.innerText),
                ["Total", "Company", "xphone", "xpad", "individual"],
                "The row headers should be as expected"
            );

            // open groupby menu generator and add a new groupby
            await toggleGroupByMenu(target);
            await toggleAddCustomGroup(target);
            await selectGroup(target, "bar");
            await applyGroup(target);

            assert.deepEqual(
                [...target.querySelectorAll("thead th")].map((th) => th.innerText),
                ["", "Total", "Foo"],
                "The col headers should be as expected"
            );
            assert.deepEqual(
                [...target.querySelectorAll("tbody th")].map((th) => th.innerText),
                ["Total", "Company", "Yes", "individual", "No", "Yes"],
                "The row headers should be as expected"
            );
        }
    );

    QUnit.test("display only one dropdown menu", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        // add a col groupby on Product
        await click(target.querySelector("thead th.o_pivot_header_cell_closed"));
        await click(target.querySelectorAll("thead .dropdown-menu .dropdown-item")[5]);

        // Click on the two header dropdown togglers
        await click(target.querySelectorAll("thead th.o_pivot_header_cell_closed")[0]);
        await click(target.querySelectorAll("thead th.o_pivot_header_cell_closed")[1]);

        assert.containsOnce(
            target,
            "thead .dropdown-menu",
            "Only one dropdown should be displayed at a time"
        );
    });

    QUnit.test("Server order is kept by default", async function (assert) {
        assert.expect(1);

        let isSecondReadGroup = false;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="customer" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    if (isSecondReadGroup) {
                        return Promise.resolve([
                            {
                                customer: [2, "Second"],
                                foo: 18,
                                __count: 2,
                                __domain: [["customer", "=", 2]],
                            },
                            {
                                customer: [1, "First"],
                                foo: 14,
                                __count: 2,
                                __domain: [["customer", "=", 1]],
                            },
                        ]);
                    }
                    isSecondReadGroup = true;
                }
            },
        });

        const values = [
            "32", // Total Value
            "18", // Second
            "14", // First
        ];
        assert.strictEqual(getCurrentValues(target), values.join());
    });

    QUnit.test("pivot rendering with boolean field", async function (assert) {
        assert.expect(4);

        serverData.models.partner.fields.bar = {
            string: "bar",
            type: "boolean",
            store: true,
            searchable: true,
            group_operator: "bool_or",
        };
        serverData.models.partner.records = [
            { id: 1, bar: true, date: "2019-12-14" },
            { id: 2, bar: false, date: "2019-05-14" },
        ];

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="date" type="row" interval="day"/>
                    <field name="bar" type="col"/>
                    <field name="bar" string="SLA status Failed" type="measure"/>
                </pivot>`,
        });

        assert.strictEqual(
            $(target).find('tbody tr:contains("2019-12-14")').length,
            1,
            "There should be a first column"
        );
        assert.ok(
            $(target).find('tbody tr:contains("2019-12-14") [type="checkbox"]').is(":checked"),
            "first column contains checkbox and value should be ticked"
        );
        assert.strictEqual(
            $(target).find('tbody tr:contains("2019-05-14")').length,
            1,
            "There should be a second column"
        );
        assert.notOk(
            $(target).find('tbody tr:contains("2019-05-14") [type="checkbox"]').is(":checked"),
            "second column should have checkbox that is not checked by default"
        );
    });

    QUnit.test("empty pivot view with action helper", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                <pivot>
                    <field name="product_id" type="measure"/>
                    <field name="date" interval="month" type="col"/>
                </pivot>`,
            "partner,false,search": `
                <search>
                    <filter name="small_than_0" string="Small Than 0" domain="[('id', '&lt;', 0)]"/>
                </search>`,
        };
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            context: { search_default_small_than_0: true },
            noContentHelp: markup('<p class="abc">click to add a foo</p>'),
            config: {
                views: [[false, "search"]],
            },
        });

        assert.containsOnce(target, ".o_view_nocontent .abc");
        assert.containsNone(target, "table");

        await removeFacet(target);

        assert.containsNone(target, ".o_view_nocontent .abc");
        assert.containsOnce(target, "table");
    });

    QUnit.test("empty pivot view with sample data", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                <pivot sample="1">
                    <field name="product_id" type="measure"/>
                    <field name="date" interval="month" type="col"/>
                </pivot>`,
            "partner,false,search": `
                <search>
                    <filter name="small_than_0" string="Small Than 0" domain="[('id', '&lt;', 0)]"/>
                </search>`,
        };

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            context: { search_default_small_than_0: true },
            noContentHelp: markup('<p class="abc">click to add a foo</p>'),
            config: {
                views: [[false, "search"]],
            },
        });

        assert.hasClass(target.querySelector(".o_pivot_view .o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_view_nocontent .abc");

        await removeFacet(target);

        assert.doesNotHaveClass(
            target.querySelector(".o_pivot_view .o_content"),
            "o_view_sample_data"
        );
        assert.containsNone(target, ".o_view_nocontent .abc");
        assert.containsOnce(target, "table");
    });

    QUnit.test("non empty pivot view with sample data", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                <pivot sample="1">
                    <field name="product_id" type="measure"/>
                    <field name="date" interval="month" type="col"/>
                </pivot>`,
            "partner,false,search": `
                <search>
                    <filter name="small_than_0" string="Small Than 0" domain="[('id', '&lt;', 0)]"/>
                </search>`,
        };

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            noContentHelp: markup('<p class="abc">click to add a foo</p>'),
            config: {
                views: [[false, "search"]],
            },
        });

        assert.doesNotHaveClass(target, "o_view_sample_data");
        assert.containsNone(target, ".o_view_nocontent .abc");
        assert.containsOnce(target, "table");

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Small Than 0");

        assert.doesNotHaveClass(target, "o_view_sample_data");
        assert.containsOnce(target, ".o_view_nocontent .abc");
        assert.containsNone(target, "table");
    });

    QUnit.test("pivot is reloaded when leaving and coming back", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                <pivot>
                    <field name="customer" type="row"/>
                </pivot>`,
            "partner,false,search": `<search/>`,
            "partner,false,list": '<tree><field name="foo"/></tree>',
        };

        const mockRPC = (route, args) => {
            assert.step(args.method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "pivot"],
                [false, "list"],
            ],
        });

        assert.containsOnce(target, ".o_pivot_view");
        assert.strictEqual(getCurrentValues(target), ["4", "2", "2"].join(","));

        assert.verifySteps(["/web/webclient/load_menus", "get_views", "read_group", "read_group"]);

        // switch to list view
        await click(target.querySelector(".o_control_panel .o_switch_view.o_list"));
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_list_view");
        assert.verifySteps(["web_search_read"]);

        // switch back to pivot
        await click(target.querySelector(".o_control_panel .o_switch_view.o_pivot"));

        assert.containsOnce(target, ".o_pivot_view");
        assert.strictEqual(getCurrentValues(target), ["4", "2", "2"].join(","));

        assert.verifySteps(["read_group", "read_group"]);
    });

    QUnit.test("expanded groups are kept when leaving and coming back", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                <pivot>
                    <field name="customer" type="row"/>
                </pivot>`,
            "partner,false,search": `<search/>`,
            "partner,false,list": '<tree><field name="foo"/></tree>',
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "pivot"],
                [false, "list"],
            ],
        });

        assert.containsOnce(target, ".o_pivot_view");
        assert.strictEqual(getCurrentValues(target), ["4", "2", "2"].join(","));

        // drill down first row group (group by company_type)
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        await click(target.querySelector(".o_pivot .dropdown-menu .dropdown-item"));

        assert.strictEqual(getCurrentValues(target), ["4", "2", "1", "1", "2"].join(","));

        // switch to list view
        await click(target.querySelector(".o_control_panel .o_switch_view.o_list"));
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_list_view");

        // switch back to pivot
        await click(target.querySelector(".o_control_panel .o_switch_view.o_pivot"));

        assert.containsOnce(target, ".o_pivot_view");
        assert.strictEqual(getCurrentValues(target), ["4", "2", "1", "1", "2"].join(","));
    });

    QUnit.test("sorted rows are kept when leaving and coming back", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                <pivot>
                    <field name="foo" type="measure"/>
                    <field name="product_id" type="row"/>
                </pivot>`,
            "partner,false,search": `<search/>`,
            "partner,false,list": '<tree><field name="foo"/></tree>',
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "pivot"],
                [false, "list"],
            ],
        });

        assert.containsOnce(target, ".o_pivot_view");
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        // sort the first group
        await click(target.querySelector("th.o_pivot_measure_row"));
        await click(target.querySelector("th.o_pivot_measure_row"));

        assert.strictEqual(getCurrentValues(target), ["32", "20", "12"].join(","));

        // switch to list view
        await click(target.querySelector(".o_control_panel .o_switch_view.o_list"));
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_list_view");

        // switch back to pivot
        await click(target.querySelector(".o_control_panel .o_switch_view.o_pivot"));

        assert.containsOnce(target, ".o_pivot_view");
        assert.strictEqual(getCurrentValues(target), ["32", "20", "12"].join(","));
    });

    QUnit.test("correctly handle concurrent reloads", async function (assert) {
        serverData.views = {
            "partner,false,pivot": `
                <pivot>
                    <field name="foo" type="measure"/>
                    <field name="product_id" type="row"/>
                </pivot>`,
            "partner,false,search": `<search/>`,
            "partner,false,list": '<tree><field name="foo"/></tree>',
        };

        let def;
        let readGroupCount = 0;
        const mockRPC = (route, args) => {
            if (args.method === "read_group" && def) {
                readGroupCount++;
                if (readGroupCount === 2) {
                    // slow down last read_group of first reload
                    return Promise.resolve(def);
                }
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "pivot"],
                [false, "list"], // s.t. there is a pivot view switcher
            ],
        });

        assert.containsOnce(target, ".o_pivot_view");
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        // drill down first row group (group by company_type)
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        await click(target.querySelector(".o_pivot .dropdown-menu .dropdown-item"));

        assert.strictEqual(getCurrentValues(target), ["32", "12", "12", "20"].join(","));

        // reload twice by clicking on pivot view switcher
        def = makeDeferred();
        await click(target.querySelector(".o_control_panel .o_switch_view.o_pivot"));
        await click(target.querySelector(".o_control_panel .o_switch_view.o_pivot"));

        def.resolve();
        await nextTick();

        assert.strictEqual(getCurrentValues(target), ["32", "12", "12", "20"].join(","));
    });

    QUnit.test("consecutively toggle several measures", async function (assert) {
        let def;
        serverData.models.partner.fields.foo2 = {
            ...serverData.models.partner.fields.foo,
            string: "Foo2",
            store: true,
        };

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                    <field name="product_id" type="row"/>
                </pivot>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    return Promise.resolve(def);
                }
            },
        });

        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        // Toggle several measures (the reload is blocked, so all measures should be toggled in once)
        def = makeDeferred();
        await toggleMenu(target, "Measures");
        await toggleMenuItem(target, "Foo2"); // add foo2
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));
        await toggleMenuItem(target, "Foo"); // remove foo
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));
        await toggleMenuItem(target, "Count"); // add count
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        def.resolve();
        await nextTick();

        assert.strictEqual(getCurrentValues(target), ["0", "4", "0", "1", "0", "3"].join(","));
    });

    QUnit.test("flip axis while loading a filter", async function (assert) {
        let def;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
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
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    return Promise.resolve(def);
                }
            },
        });

        const values = ["2", "1", "29", "32", "12", "12", "2", "1", "17", "20"];
        assert.strictEqual(getCurrentValues(target), values.join(","));

        // Set a domain (this reload is delayed)
        def = makeDeferred();
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter");
        assert.strictEqual(getCurrentValues(target), values.join(","));

        // Flip axis
        await click(target.querySelector(".o_pivot_flip_button"));
        assert.strictEqual(getCurrentValues(target), values.join(","));

        def.resolve();
        await nextTick();

        assert.strictEqual(getCurrentValues(target), ["20", "2", "1", "17"].join(","));
    });

    QUnit.test("sort rows while loading a filter", async function (assert) {
        let def;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                    <field name="product_id" type="row"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="my_filter" string="My Filter" domain="[('product_id', '=', 41)]"/>
                </search>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    return Promise.resolve(def);
                }
            },
        });

        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        // Set a domain (this reload is delayed)
        def = makeDeferred();
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter");
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        // Sort rows (this operation should be ignored as it concerns the old
        // table, which will be replaced soon)
        await click(target.querySelector("th.o_pivot_measure_row"));
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        def.resolve();
        await nextTick();

        assert.strictEqual(getCurrentValues(target), ["20", "20"].join(","));
    });

    QUnit.test("close a group while loading a filter", async function (assert) {
        let def;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                    <field name="product_id" type="row"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="my_filter" string="My Filter" domain="[('product_id', '=', 41)]"/>
                </search>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    return Promise.resolve(def);
                }
            },
        });

        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        // Set a domain (this reload is delayed)
        def = makeDeferred();
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter");
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        // Close a group (this operation should be ignored as it concerns the old
        // table, which will be replaced soon)
        await click(target.querySelector("tbody .o_pivot_header_cell_opened"));
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        def.resolve();
        await nextTick();

        assert.strictEqual(getCurrentValues(target), ["20", "20"].join(","));
    });

    QUnit.test("add a groupby while loading a filter", async function (assert) {
        let def;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                    <field name="product_id" type="row"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="my_filter" string="My Filter" domain="[('product_id', '=', 41)]"/>
                </search>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    return Promise.resolve(def);
                }
            },
        });

        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        // Set a domain (this reload is delayed)
        def = makeDeferred();
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter");
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        // Add a groupby (this operation should be ignored as it concerns the old
        // table, which will be replaced soon)
        await click(target.querySelector("thead .o_pivot_header_cell_closed"));
        await click(target.querySelector("thead .dropdown-menu .dropdown-item"));
        assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

        def.resolve();
        await nextTick();

        assert.strictEqual(getCurrentValues(target), ["20", "20"].join(","));
    });

    QUnit.test("expand a group while loading a filter", async function (assert) {
        let def;
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                    <field name="product_id" type="row"/>
                </pivot>`,
            searchViewArch: `
                <search>
                    <filter name="my_filter" string="My Filter" domain="[('product_id', '=', 41)]"/>
                </search>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    return Promise.resolve(def);
                }
            },
        });

        // Add a groupby, to have a group to expand afterwards
        await click(target.querySelector("tbody .o_pivot_header_cell_closed"));
        await click(target.querySelector("tbody .dropdown-menu .dropdown-item"));

        assert.strictEqual(getCurrentValues(target), ["32", "12", "12", "20"].join(","));

        // Set a domain (this reload is delayed)
        def = makeDeferred();
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter");
        assert.strictEqual(getCurrentValues(target), ["32", "12", "12", "20"].join(","));

        // Expand a group (this operation should be ignored as it concerns the old
        // table, which will be replaced soon)
        await click(target.querySelectorAll("tbody .o_pivot_header_cell_closed")[1]);
        assert.strictEqual(getCurrentValues(target), ["32", "12", "12", "20"].join(","));

        def.resolve();
        await nextTick();

        assert.strictEqual(getCurrentValues(target), ["20", "20"].join(","));
    });

    QUnit.test(
        "concurrent reloads: add a filter, and directly toggle a measure",
        async function (assert) {
            let def;
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot>
                        <field name="foo" type="measure"/>
                        <field name="product_id" type="row"/>
                    </pivot>`,
                searchViewArch: `
                    <search>
                        <filter name="my_filter" string="My Filter" domain="[('product_id', '=', 37)]"/>
                    </search>`,
                mockRPC(route, args) {
                    if (args.method === "read_group") {
                        return Promise.resolve(def);
                    }
                },
            });

            assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

            // Set a domain (this reload is delayed)
            def = makeDeferred();
            await toggleFilterMenu(target);
            await toggleMenuItem(target, "My Filter");

            assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

            // Toggle a measure
            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Count");

            assert.strictEqual(getCurrentValues(target), ["32", "12", "20"].join(","));

            def.resolve();
            await nextTick();

            assert.strictEqual(getCurrentValues(target), ["12", "1", "12", "1"].join(","));
        }
    );

    QUnit.test(
        "if no measure is set in arch, 'Count' is used as measure initially",
        async function (assert) {
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `<pivot/>`,
            });

            assert.deepEqual(
                [...target.querySelectorAll("thead th")].map((e) => e.innerText),
                ["", "Total", "Count"]
            );
        }
    );

    QUnit.test(
        "if (at least) one measure is set in arch and display_quantity is false or unset, 'Count' is not used as measure initially",
        async function (assert) {
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                <pivot>
                    <field name="foo" type="measure"/>
                </pivot>
            `,
            });

            assert.deepEqual(
                [...target.querySelectorAll("thead th")].map((e) => e.innerText),
                ["", "Total", "Foo"]
            );
        }
    );

    QUnit.test(
        "if (at least) one measure is set in arch and display_quantity is true, 'Count' is used as measure initially",
        async function (assert) {
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                <pivot display_quantity="1">
                    <field name="foo" type="measure"/>
                </pivot>
            `,
            });

            assert.deepEqual(
                [...target.querySelectorAll("thead th")].map((e) => e.innerText),
                ["", "Total", "Count", "Foo"]
            );
        }
    );

    QUnit.test("'Measures' menu when there is no measurable fields", async function (assert) {
        serverData.models.partner = {
            fields: {},
            records: [{ id: 1, display_name: "The one" }],
        };
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `<pivot/>`,
        });

        await toggleMenu(target, "Measures");

        // "Count" is the only measure available
        assert.deepEqual(
            [...target.querySelectorAll(".o_cp_bottom_left .dropdown-menu .o_menu_item")].map(
                (e) => e.innerText
            ),
            ["Count"]
        );
        // No separator should be displayed in the menu "Measures"
        assert.containsNone(target, ".o_cp_bottom_left .dropdown-menu div.dropdown-divider");
    });

    QUnit.test(
        "comparison with two groupbys: rows from reference period should be displayed",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.records = [
                { id: 1, date: "2021-10-10", product_id: 1, customer: 1 },
                { id: 2, date: "2020-10-10", product_id: 2, customer: 1 },
            ];
            serverData.models.product.records = [
                { id: 1, display_name: "A" },
                { id: 2, display_name: "B" },
            ];
            serverData.models.customer.records = [{ id: 1, display_name: "P" }];

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                <pivot>
                    <field name="customer" type="row"/>
                    <field name="product_id" type="row"/>
                </pivot>
            `,
                searchViewArch: `
                <search>
                    <filter name='date' date='date'/>
                </search>
            `,
            });

            // compare 2021 to 2020
            await toggleFilterMenu(target);
            await toggleMenuItem(target, "Date");
            await toggleMenuItemOption(target, "Date", "2021");
            await toggleComparisonMenu(target);
            await toggleMenuItem(target, 0);

            assert.deepEqual(
                [...target.querySelectorAll("th")].slice(0, 6).map((el) => el.innerText),
                ["", "Total", "Count", "2020", "2021", "Variation"],
                "The col headers should be as expected"
            );

            assert.deepEqual(
                [...target.querySelectorAll("th")].slice(6).map((el) => el.innerText),
                ["Total", "P", "B", "A"],
                "The row headers should be as expected"
            );

            const values = ["1", "1", "0%", "1", "1", "0%", "1", "0", "-100%", "0", "1", "100%"];
            assert.strictEqual(getCurrentValues(target), values.join());
        }
    );

    QUnit.test("pivot_row_groupby should be also used after first load", async function (assert) {
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

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `<pivot/>`,
            searchViewArch: `
                <search>
                    <filter name='product_id' string="Product" context="{'group_by':'product_id'}"/>
                    <filter name='customer' string="Customer" context="{'group_by':'customer'}"/>
                </search>
            `,
            groupBy: ["bar"],
            mockRPC(route, args) {
                if (args.method === "create_or_replace") {
                    assert.deepEqual(args.args[0].context, expectedContexts.shift());
                    return ids.shift();
                }
            },
        });

        assert.deepEqual(
            [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
            ["Total", "No", "Yes"],
            "The row headers should be as expected"
        );

        await click(target.querySelector("tbody th")); // click on row header "Total"
        await click(target.querySelector("tbody th")); // click on row header "Total"
        await click(target.querySelector("tbody .o_group_by_menu .o_menu_item")); // select "Product"

        assert.deepEqual(
            [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
            ["Total", "xphone", "xpad"],
            "The row headers should be as expected"
        );

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "Favorite");
        await saveFavorite(target);

        assert.deepEqual(
            [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
            ["Total", "xphone", "xpad"],
            "The row headers should be as expected"
        );

        await removeFacet(target);

        assert.deepEqual(
            [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
            ["Total", "No", "Yes"],
            "The row headers should be as expected"
        );

        await toggleFavoriteMenu(target);
        await toggleMenuItem(target, "Favorite");

        assert.deepEqual(
            [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
            ["Total", "xphone", "xpad"],
            "The row headers should be as expected"
        );

        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Customer");

        assert.deepEqual(
            [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
            ["Total", "xphone", "First", "xpad", "First", "Second"],
            "The row headers should be as expected"
        );

        await click(target.querySelector("tbody th")); // click on row header "Total"
        await click(target.querySelector("tbody th")); // click on row header "Total"
        await click(target.querySelectorAll("tbody .o_group_by_menu .o_menu_item")[1]); // select "Customer"

        assert.deepEqual(
            [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
            ["Total", "First", "Second"],
            "The row headers should be as expected"
        );

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "Favorite 2");
        await saveFavorite(target);

        assert.deepEqual(
            [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
            ["Total", "First", "Second"],
            "The row headers should be as expected"
        );
    });

    QUnit.test(
        "pivot_row_groupby should be also used after first load (2)",
        async function (assert) {
            await makeView({
                serverData,
                type: "pivot",
                resModel: "partner",
                groupBy: ["product_id"],
                arch: `<pivot/>`,
                irFilters: [
                    {
                        user_id: [2, "Mitchell Admin"],
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

            assert.deepEqual(
                [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
                ["Total", "xphone", "xpad"],
                "The row headers should be as expected"
            );

            await toggleFavoriteMenu(target);
            await toggleMenuItem(target, "Favorite");

            assert.deepEqual(
                [...target.querySelectorAll("th")].slice(3).map((el) => el.innerText),
                ["Total", "First", "Second"],
                "The row headers should be as expected"
            );
        }
    );

    QUnit.test(
        "specific pivot keys in action context must have less importance than in favorite context",
        async function (assert) {
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `<pivot/>`,
                context: {
                    pivot_column_groupby: [],
                    pivot_measures: ["__count"],
                    pivot_row_groupby: [],
                },
                irFilters: [
                    {
                        user_id: [2, "Mitchell Admin"],
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
                        user_id: [2, "Mitchell Admin"],
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

            assert.deepEqual(
                [...target.querySelectorAll("th")].slice(1, 6).map((el) => el.innerText),
                ["Total", "", "No", "Yes", "Computed and not stored"]
            );

            await toggleFavoriteMenu(target);
            await toggleMenuItem(target, "My favorite 2");

            assert.deepEqual(
                [...target.querySelectorAll("th")].slice(1, 11).map((el) => el.innerText),
                [
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
                ]
            );
        }
    );

    QUnit.test(
        "favorite pivot_measures should be used even if found also in global context",
        async function (assert) {
            serverData.models.partner.fields.computed_field.store = true; // --> Computed and not stored displayed in "Measures" menu

            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `<pivot/>`,
                context: {
                    pivot_measures: ["__count"],
                },
                mockRPC(route, args) {
                    if (args.method === "create_or_replace") {
                        assert.deepEqual(args.args[0].context, {
                            group_by: [],
                            pivot_column_groupby: [],
                            pivot_measures: ["computed_field"],
                            pivot_row_groupby: [],
                        });
                        return 1;
                    }
                },
            });

            assert.deepEqual(
                [...target.querySelectorAll("th")].slice(1, 3).map((el) => el.innerText),
                ["Total", "Count"]
            );

            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Count");
            await toggleMenuItem(target, "Computed and not stored");

            assert.deepEqual(getFacetTexts(target), []);
            assert.deepEqual(
                [...target.querySelectorAll("th")].slice(1, 3).map((el) => el.innerText),
                ["Total", "Computed and not stored"]
            );

            await toggleFavoriteMenu(target);
            await toggleSaveFavorite(target);
            await editFavoriteName(target, "Favorite");
            await saveFavorite(target);

            assert.deepEqual(getFacetTexts(target), ["Favorite"]);
            assert.deepEqual(
                [...target.querySelectorAll("th")].slice(1, 3).map((el) => el.innerText),
                ["Total", "Computed and not stored"]
            );
        }
    );

    QUnit.test(
        "no class 'o_view_sample_data' when real data are presented",
        async function (assert) {
            serverData.models.partner.fields.foo.store = true;
            serverData.models.partner.records = [];
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: `
                    <pivot sample="1">
                        <field name="product_id" type="row"/>
                    </pivot>
                `,
            });

            assert.containsOnce(target, ".o_pivot_view .o_view_sample_data");
            assert.containsOnce(target, ".o_pivot_view table");
            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Foo");
            assert.containsNone(target, ".o_pivot_view .o_view_sample_data");
            assert.containsNone(target, ".o_pivot_view table");
        }
    );
});
