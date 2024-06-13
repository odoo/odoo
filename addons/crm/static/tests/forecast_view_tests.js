/** @odoo-module **/

import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { menuService } from "@web/webclient/menus/menu_service";
import {
    toggleSearchBarMenu,
    toggleMenuItem,
    toggleMenuItemOption,
} from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { mock } from "@web/../tests/legacy_tests/helpers/test_utils";
import { browser } from "@web/core/browser/browser";

const patchDate = mock.patchDate;

const serviceRegistry = registry.category("services");

const forecastDomain = (forecastStart) => {
    return ["|", ["date_field", "=", false], ["date_field", ">=", forecastStart]];
};

let serverData;
let target;
QUnit.module("Views", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        date_field: {
                            string: "Date Field",
                            type: "date",
                            store: true,
                            sortable: true,
                        },
                        bar: {
                            string: "Bar",
                            type: "many2one",
                            relation: "partner",
                            store: true,
                            sortable: true,
                        },
                        value: {
                            string: "Value",
                            type: "float",
                            store: true,
                            sortable: true,
                        },
                        number: {
                            string: "Number",
                            type: "integer",
                            store: true,
                            sortable: true,
                        }
                    },
                    records: [],
                },
                partner: {},
            },
            views: {
                "foo,false,legacy_toy": `<legacy_toy/>`,
                "foo,false,graph": `<graph js_class="forecast_graph"/>`,
                "foo,false,search": `
                    <search>
                        <filter name="forecast_filter" string="Forecast Filter" context="{ 'forecast_filter': 1 }"/>
                        <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                        <filter name="group_by_date_field" string="Date Field" context="{ 'group_by': 'date_field' }"/>
                    </search>
                `,
            },
        };
        setupViewRegistries();
        serviceRegistry.add("menu", menuService);

        target = getFixture();
    });

    QUnit.module("Forecast views");

    QUnit.test("Forecast graph view", async function (assert) {
        assert.expect(5);

        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        const unpatchDate = patchDate(2021, 8, 16, 16, 54, 0);

        const expectedDomains = [
            forecastDomain("2021-09-01"), // month granularity due to no groupby
            forecastDomain("2021-09-16"), // day granularity due to simple bar groupby
            // quarter granularity due to date field groupby activated with quarter interval option
            forecastDomain("2021-07-01"),
            // quarter granularity due to date field groupby activated with quarter and year interval option
            forecastDomain("2021-01-01"),
            // forecast filter no more active
            [],
        ];

        await makeView({
            resModel: "foo",
            type: "graph",
            serverData,
            searchViewId: false,
            context: {
                search_default_forecast_filter: 1,
                forecast_field: "date_field",
            },
            mockRPC(_, args) {
                if (args.method === "web_read_group") {
                    const { domain } = args.kwargs;
                    assert.deepEqual(domain, expectedDomains.shift());
                }
            },
        });

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Bar");

        await toggleMenuItem(target, "Date Field");
        await toggleMenuItemOption(target, "Date Field", "Quarter");

        await toggleMenuItemOption(target, "Date Field", "Year");

        await toggleMenuItem(target, "Forecast Filter");

        unpatchDate();
    });

    QUnit.test(
        "forecast filter domain is combined with other domains following the same rules as other filters (OR in same group, AND between groups)",
        async function (assert) {
            assert.expect(1);

            const unpatchDate = patchDate(2021, 8, 16, 16, 54, 0);

            serverData.views["foo,false,search"] = `
                <search>
                    <filter name="other_group_filter" string="Other Group Filter" domain="[('number', '>', 2)]"/>
                    <separator/>
                    <filter name="same_group_filter" string="Same Group Filter" domain="[('bar', '=', 2)]"/>
                    <filter name="forecast_filter" string="Forecast Filter" context="{ 'forecast_filter': 1 }" domain="[('value', '>', 0.0)]"/>
                </search>
            `;

            await makeView({
                resModel: "foo",
                type: "graph",
                serverData,
                searchViewId: false,
                context: {
                    search_default_same_group_filter: 1,
                    search_default_forecast_filter: 1,
                    search_default_other_group_filter: 1,
                    forecast_field: "date_field",
                },
                mockRPC(_, args) {
                    if (args.method === "web_read_group") {
                        const { domain } = args.kwargs;
                        assert.deepEqual(domain, [
                            "&",
                            ["number", ">", 2],
                            "|",
                            ["bar", "=", 2],
                            "&",
                            ["value", ">", 0.0],
                            "|",
                            ["date_field", "=", false],
                            ["date_field", ">=", "2021-09-01"],
                        ]);
                    }
                },
            });

            unpatchDate();
        }
    );
});
