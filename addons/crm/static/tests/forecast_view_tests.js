/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { makeView } from "@web/../tests/views/helpers";
import { mock } from "web.test_utils";
import { registry } from "@web/core/registry";
import {
    setupControlPanelServiceRegistry,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenuItem,
    toggleMenuItemOption,
} from "@web/../tests/search/helpers";

const patchDate = mock.patchDate;

const serviceRegistry = registry.category("services");

let serverData;
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
                    },
                    records: [],
                },
            },
            views: {
                "foo,false,legacy_toy": `<legacy_toy/>`,
                "foo,false,graph": `<graph js_class="forecast_graph"/>`,
                "foo,false,search": `
                    <search>
                        <filter name="forecast_filter" string="Forecast Filter" context="{ 'forecast_field': 'date_field' }"/>
                        <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                        <filter name="group_by_date_field" string="Date Field" context="{ 'group_by': 'date_field' }"/>
                    </search>
                `,
            },
        };
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
    });

    QUnit.module("Forecast views");

    QUnit.test("Forecast graph view", async function (assert) {
        assert.expect(5);

        const unpatchDate = patchDate(2021, 8, 16, 16, 54, 0);

        const forecastDomain = (forecastStart) => {
            return ["|", ["date_field", "=", false], ["date_field", ">=", forecastStart]];
        };

        const expectedDomains = [
            forecastDomain("2021-09-01"), // month granularity due to no groupby
            forecastDomain("2021-09-16"), // day granularity due to simple bar groupby
            forecastDomain("2021-07-01"), // quarter granularity due to date field groupby activated with quarter interval option
            forecastDomain("2021-01-01"),  // quarter granularity due to date field groupby activated with quarter and year interval option
            [], // forecast filter no more active
        ];

        const forecastGraph = await makeView({
            resModel: "foo",
            type: "forecast_graph",
            serverData,
            searchViewId: false,
            context: { search_default_forecast_filter: 1 },
            mockRPC(_, args) {
                if (args.method === "web_read_group") {
                    const { domain } = args.kwargs;
                    assert.deepEqual(domain, expectedDomains.shift());
                }
            },
        });

        await toggleGroupByMenu(forecastGraph);
        await toggleMenuItem(forecastGraph, "Bar");

        await toggleMenuItem(forecastGraph, "Date Field");
        await toggleMenuItemOption(forecastGraph, "Date Field", "Quarter");

        await toggleMenuItemOption(forecastGraph, "Date Field", "Year");

        await toggleFilterMenu(forecastGraph);
        await toggleMenuItem(forecastGraph, "Forecast Filter");

        unpatchDate();
    });
});
