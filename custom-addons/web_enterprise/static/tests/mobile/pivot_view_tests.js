/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    makeFakeLocalizationService,
    makeFakeUserService,
} from "@web/../tests/helpers/mock_services";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "@web/../tests/search/helpers";
import { makeView } from "@web/../tests/views/helpers";
import { browser } from "@web/core/browser/browser";

const serviceRegistry = registry.category("services");

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
        assert.expect(2);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="measure"/>
                </pivot>`,
        });

        assert.hasClass(target.querySelector(".o_pivot_view"), "o_view_controller");
        assert.containsOnce(
            target,
            "td.o_pivot_cell_value:contains(32)",
            "should contain a pivot cell with the sum of all records"
        );
    });

    QUnit.test("unselecting all measures should not crash pivot rendering", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: `
            <pivot string="Partners">
            <field name="foo" type="measure"/>
            </pivot>`,
        });

        await click(target.getElementsByClassName("dropdown-toggle btn btn-primary")[1]);
        await click(target.getElementsByClassName("dropdown-item o_menu_item selected")[0]);

        assert.containsOnce(
            target,
            "div.o_nocontent_help",
            "Instead of error action helper will appear"
        );
    });
});
