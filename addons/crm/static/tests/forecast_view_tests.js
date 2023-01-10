/** @odoo-module **/

import { legacyExtraNextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import {
    setupControlPanelServiceRegistry,
    switchView,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenuItem,
    toggleMenuItemOption,
} from "@web/../tests/search/helpers";
import { makeView } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import AbstractModel from "web.AbstractModel";
import AbstractView from "web.AbstractView";
import { controlPanel as cpHelpers, mock } from "web.test_utils";
import legacyViewRegistry from "web.view_registry";
import { browser } from "@web/core/browser/browser";

const patchDate = mock.patchDate;

const serviceRegistry = registry.category("services");

const forecastDomain = (forecastStart) => {
    return ["|", ["date_field", "=", false], ["date_field", ">=", forecastStart]];
};

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
                        <filter name="forecast_filter" string="Forecast Filter" context="{ 'forecast_filter': 1 }"/>
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

        const forecastGraph = await makeView({
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

        await toggleGroupByMenu(forecastGraph);
        await toggleMenuItem(forecastGraph, "Bar");

        await toggleMenuItem(forecastGraph, "Date Field");
        await toggleMenuItemOption(forecastGraph, "Date Field", "Quarter");

        await toggleMenuItemOption(forecastGraph, "Date Field", "Year");

        await toggleFilterMenu(forecastGraph);
        await toggleMenuItem(forecastGraph, "Forecast Filter");

        unpatchDate();
    });

    QUnit.test(
        "forecast filter domain is combined with other domains with an AND",
        async function (assert) {
            assert.expect(1);

            const unpatchDate = patchDate(2021, 8, 16, 16, 54, 0);

            serverData.views["foo,false,search"] = `
                <search>
                    <filter name="other_filter" string="Other Filter" domain="[('bar', '=', 2)]"/>
                    <filter name="forecast_filter" string="Forecast Filter" context="{ 'forecast_filter': 1 }"/>
                </search>
            `;

            await makeView({
                resModel: "foo",
                type: "graph",
                serverData,
                searchViewId: false,
                context: {
                    search_default_other_filter: 1,
                    search_default_forecast_filter: 1,
                    forecast_field: "date_field",
                },
                mockRPC(_, args) {
                    if (args.method === "web_read_group") {
                        const { domain } = args.kwargs;
                        assert.deepEqual(domain, [
                            "&",
                            ["bar", "=", 2],
                            "|",
                            ["date_field", "=", false],
                            ["date_field", ">=", "2021-09-01"],
                        ]);
                    }
                },
            });

            // note that the facets of the two filters are combined with an OR.
            // --> current behavior in legacy

            unpatchDate();
        }
    );

    /** @todo remove this legacy test when conversion of all forecast views is done */
    QUnit.test(
        "legacy and new forecast views can share search model state",
        async function (assert) {
            assert.expect(16);

            patchWithCleanup(browser, { setTimeout: (fn) => fn() });
            const unpatchDate = patchDate(2021, 8, 16, 16, 54, 0);

            const expectedDomains = [
                // first doAction
                forecastDomain("2021-09-01"), // initial load of forecast_graph
                forecastDomain("2021-07-01"), // toggle date field groupby with quarter option
                forecastDomain("2021-07-01"), // initial load of legacy_toy
                forecastDomain("2021-01-01"), // toggle date field groupby with year option
                forecastDomain("2021-01-01"), // switch back to forecast_graph

                // second doAction

                forecastDomain("2021-09-01"), // initial load of legacy_toy
                forecastDomain("2021-07-01"), // toggle date field groupby with quarter option
                forecastDomain("2021-07-01"), // switch to forecast_graph
                forecastDomain("2021-01-01"), // toggle date field groupby with year option
                forecastDomain("2021-01-01"), // switch back to legacy_toy
            ];

            patchWithCleanup(AbstractModel.prototype, {
                async load(params) {
                    assert.deepEqual(params.domain, expectedDomains.shift());
                    return this._super(...arguments);
                },
                async reload(_, params) {
                    assert.deepEqual(params.domain, expectedDomains.shift());
                    return this._super(...arguments);
                },
            });

            const LegacyForecastView = AbstractView.extend({
                display_name: _lt("Legacy toy view"),
                icon: "fa fa-bars",
                multiRecord: true,
                viewType: "legacy_toy",
                searchMenuTypes: ["filter", "groupBy"],

                _createSearchModel(params, extraExtensions = {}) {
                    Object.assign(extraExtensions, { forecast: {} });
                    return this._super(params, extraExtensions);
                },
            });

            legacyViewRegistry.add("legacy_toy", LegacyForecastView);

            const webClient = await createWebClient({
                serverData,
                mockRPC(_, args) {
                    if (args.method === "web_read_group") {
                        const { domain } = args.kwargs;
                        assert.deepEqual(domain, expectedDomains.shift());
                    }
                },
            });

            // first doAction forecast_graph -> legacy_toy -> forecast_graph

            await doAction(webClient, {
                name: "Action name",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "graph"],
                    [false, "legacy_toy"],
                ],
                context: {
                    search_default_forecast_filter: 1,
                    forecast_field: "date_field",
                },
            });

            assert.containsOnce(webClient, ".o_switch_view.o_graph.active");

            await toggleGroupByMenu(webClient);
            await toggleMenuItem(webClient, "Date Field");
            await toggleMenuItemOption(webClient, "Date Field", "Quarter");

            await switchView(webClient, "legacy_toy");
            await legacyExtraNextTick();

            assert.containsOnce(webClient, ".o_switch_view.o_legacy_toy.active");

            await cpHelpers.toggleGroupByMenu(webClient);
            await toggleMenuItem(webClient, "Date Field");
            await toggleMenuItemOption(webClient, "Date Field", "Year");

            await switchView(webClient, "graph");

            assert.containsOnce(webClient, ".o_switch_view.o_graph.active");

            // second doAction legacy_toy -> forecast_graph -> legacy_toy

            await doAction(webClient, {
                name: "Action name",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "legacy_toy"],
                    [false, "graph"],
                ],
                context: {
                    search_default_forecast_filter: 1,
                    forecast_field: "date_field",
                },
            });
            await legacyExtraNextTick();

            assert.containsOnce(webClient, ".o_switch_view.o_legacy_toy.active");

            await cpHelpers.toggleGroupByMenu(webClient);
            await toggleMenuItem(webClient, "Date Field");
            await toggleMenuItemOption(webClient, "Date Field", "Quarter");

            await switchView(webClient, "graph");

            assert.containsOnce(webClient, ".o_switch_view.o_graph.active");

            await toggleGroupByMenu(webClient);
            await toggleMenuItem(webClient, "Date Field");
            await toggleMenuItemOption(webClient, "Date Field", "Year");

            await switchView(webClient, "legacy_toy");
            await legacyExtraNextTick();

            assert.containsOnce(webClient, ".o_switch_view.o_legacy_toy.active");

            unpatchDate();
        }
    );
});
