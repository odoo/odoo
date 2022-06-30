/** @odoo-module **/

import { getFixture, legacyExtraNextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import {
    getFacetTexts,
    removeFacet,
    saveFavorite,
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
    switchView,
    toggleFavoriteMenu,
    toggleMenu,
    toggleMenuItem,
    toggleSaveFavorite,
} from "@web/../tests/search/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { SearchModel } from "@web/search/search_model";
import AbstractView from "web.AbstractView";
import ActionModel from "web.ActionModel";
import { mock } from "web.test_utils";
import legacyViewRegistry from "web.view_registry";
import { browser } from "@web/core/browser/browser";
import { LegacyComponent } from "@web/legacy/legacy_component";

const { xml } = owl;
const serviceRegistry = registry.category("services");
const viewRegistry = registry.category("views");

let serverData;
let target;
QUnit.module("LegacyViews", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();

        serverData = {
            models: {
                foo: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            store: true,
                            sortable: true,
                        },
                        date_field: { string: "Date", type: "date", store: true, sortable: true },
                        float_field: { string: "Float", type: "float" },
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
                "foo,false,toy": `<toy/>`,
                "foo,false,search": `
                    <search>
                        <field name="foo" operator="="/>
                        <filter name="true_domain" string="True Domain" domain="[(1, '=', 1)]"/>
                        <filter name="date_domain" string="Date Filter" date="date_field" domain="[]"/>
                        <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                        <filter name="group_by_date_field" string="Date GroupBy" context="{ 'group_by': 'date_field' }"/>
                    </search>
                `,
            },
        };
        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);

        class ToyController extends LegacyComponent {}
        ToyController.template = xml`<div class="o_toy_view"><ControlPanel /></div>`;
        ToyController.components = { ControlPanel};

        viewRegistry.add("toy", {
            type: "toy",
            display_name: _lt("Toy view"),
            multiRecord: true,
            searchMenuTypes: ["filter", "groupBy", "comparison", "favorite"],
            Controller: ToyController,
        });

        const LegacyToyView = AbstractView.extend({
            display_name: _lt("Legacy toy view"),
            icon: "fa fa-bars",
            multiRecord: true,
            viewType: "legacy_toy",
            searchMenuTypes: ["filter", "groupBy", "comparison", "favorite"],
        });

        legacyViewRegistry.add("legacy_toy", LegacyToyView);
    });

    QUnit.module("State Mappings");

    QUnit.test(
        "legacy and new views can share search model state (no favorite)",
        async function (assert) {
            assert.expect(10);

            const unpatchDate = mock.patchDate(2021, 6, 1, 10, 0, 0);

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, {
                name: "Action name",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "toy"],
                    [false, "legacy_toy"],
                ],
                context: {
                    search_default_foo: "ABC",
                    search_default_true_domain: 1,
                    search_default_date_domain: 1,
                    search_default_group_by_bar: 50,
                    search_default_group_by_date_field: 1,
                },
            });

            assert.containsOnce(target, ".o_switch_view.o_toy.active");
            assert.deepEqual(
                getFacetTexts(target).map((s) => s.replace(/\s/, "")),
                [
                    "FooABC",
                    "TrueDomainorDate Filter: July 2021",
                    "DateGroupBy: Month>Bar",
                ]
            );

            await toggleMenu(target, "Comparison");
            await toggleMenuItem(target, "Date Filter: Previous Period");

            assert.deepEqual(
                getFacetTexts(target).map((s) => s.replace(/\s/, "")),
                [
                    "FooABC",
                    "TrueDomainorDate Filter: July 2021",
                    "DateGroupBy: Month>Bar",
                    "DateFilter: Previous Period",
                ]
            );

            await switchView(target, "legacy_toy");
            await legacyExtraNextTick();

            assert.containsOnce(target, ".o_switch_view.o_legacy_toy.active");
            assert.deepEqual(
                getFacetTexts(target).map((s) => s.replace(/\s/, "")),
                [
                    "FooABC",
                    "TrueDomainorDate Filter: July 2021",
                    "DateGroupBy: Month>Bar",
                    "DateFilter: Previous Period",
                ]
            );

            await removeFacet(target, 1);

            assert.deepEqual(
                getFacetTexts(target).map((s) => s.replace(/\s/, "")),
                [
                    "FooABC",
                    "DateGroupBy: Month>Bar",
                ]
            );

            await switchView(target, "toy");

            assert.containsOnce(target, ".o_switch_view.o_toy.active");
            assert.deepEqual(
                getFacetTexts(target).map((s) => s.replace(/\s/, "")),
                [
                    "FooABC",
                    "DateGroupBy: Month>Bar",
                ]
            );

            // Check if update works
            await removeFacet(target, 1);

            assert.deepEqual(
                getFacetTexts(target).map((s) => s.replace(/\s/, "")),
                [
                    "FooABC",
                ]
            );

            await switchView(target, "legacy_toy");

            assert.deepEqual(
                getFacetTexts(target).map((s) => s.replace(/\s/, "")),
                [
                    "FooABC",
                ]
            );

            unpatchDate();
        }
    );

    QUnit.test(
        "legacy and new views can share search model state (favorite)",
        async function (assert) {
            assert.expect(6);

            serverData.models.foo.filters = [
                {
                    context: "{}",
                    domain: "[['foo', '=', 'qsdf']]",
                    id: 7,
                    is_default: true,
                    name: "My favorite",
                    sort: "[]",
                    user_id: [2, "Mitchell Admin"],
                },
            ];

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, {
                name: "Action name",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "toy"],
                    [false, "legacy_toy"],
                ],
            });

            assert.containsOnce(target, ".o_switch_view.o_toy.active");
            assert.deepEqual(getFacetTexts(target), ["My favorite"]);

            await switchView(target, "legacy_toy");
            await legacyExtraNextTick();

            assert.containsOnce(target, ".o_switch_view.o_legacy_toy.active");
            assert.deepEqual(getFacetTexts(target), ["My favorite"]);

            await switchView(target, "toy");

            assert.containsOnce(target, ".o_switch_view.o_toy.active");
            assert.deepEqual(getFacetTexts(target), ["My favorite"]);
        }
    );

    QUnit.test(
        "newly created favorite in a new view can be used in a legacy view",
        async function (assert) {
            assert.expect(5);

            patchWithCleanup(browser, { setTimeout: (fn) => fn() });
            const webClient = await createWebClient({
                serverData,
                mockRPC(_, args) {
                    if (args.method === "create_or_replace") {
                        assert.ok(typeof args.args[0].domain === "string");
                        return 7; // fake serverId to simulate the creation of
                        // the favorite in db.
                    }
                },
            });

            await doAction(webClient, {
                name: "Action name",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "toy"],
                    [false, "legacy_toy"],
                ],
            });

            assert.containsOnce(target, ".o_switch_view.o_toy.active");

            await toggleFavoriteMenu(target);
            await toggleSaveFavorite(target);
            await saveFavorite(target);

            assert.deepEqual(getFacetTexts(target), ["Action name"]);

            await switchView(target, "legacy_toy");
            await legacyExtraNextTick();

            assert.containsOnce(target, ".o_switch_view.o_legacy_toy.active");
            assert.deepEqual(getFacetTexts(target), ["Action name"]);
        }
    );

    QUnit.test(
        "legacy and new views with search model extensions can share search model state",
        async function (assert) {
            assert.expect(16);

            serverData.views[
                "foo,1,legacy_toy"
            ] = `<legacy_toy js_class="legacy_toy_with_extension"/>`;

            class SearchModelExtension extends SearchModel {
                setup() {
                    super.setup(...arguments);
                    this.toyExtension = { locationId: "Grand-Rosière" };
                }

                exportState() {
                    const exportedState = super.exportState(...arguments);
                    exportedState.toyExtension = this.toyExtension;
                    return exportedState;
                }

                _importState(state) {
                    super._importState(state);
                    this.toyExtension = state.toyExtension;
                    assert.step(JSON.stringify(state.toyExtension));
                }
            }

            const ToyView = viewRegistry.get("toy");
            ToyView.SearchModel = SearchModelExtension;

            class ToyExtension extends ActionModel.Extension {
                importState(state) {
                    super.importState(state); // done even if state is undefined in legacy code
                    assert.step(JSON.stringify(state) || "no state");
                }
                prepareState() {
                    Object.assign(this.state, {
                        locationId: "The place to be",
                    });
                }
            }
            ActionModel.registry.add("toyExtension", ToyExtension);

            const LegacyToyView = legacyViewRegistry.get("legacy_toy");

            const LegacyToyViewWithExtension = LegacyToyView.extend({
                _createSearchModel(params, extraExtensions = {}) {
                    Object.assign(extraExtensions, { toyExtension: {} });
                    return this._super(params, extraExtensions);
                },
            });
            legacyViewRegistry.add("legacy_toy_with_extension", LegacyToyViewWithExtension);

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, {
                name: "Action name",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "toy"],
                    [1, "legacy_toy"],
                ],
            });

            assert.containsOnce(target, ".o_switch_view.o_toy.active");

            await switchView(target, "legacy_toy");
            await legacyExtraNextTick();

            assert.containsOnce(target, ".o_switch_view.o_legacy_toy.active");
            assert.verifySteps([`{"locationId":"Grand-Rosière"}`]);

            await switchView(target, "toy");

            assert.containsOnce(target, ".o_switch_view.o_toy.active");
            assert.verifySteps([`{"locationId":"Grand-Rosière"}`]);

            await doAction(webClient, {
                name: "Action name",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [1, "legacy_toy"],
                    [false, "toy"],
                ],
            });
            await legacyExtraNextTick();

            assert.containsOnce(target, ".o_switch_view.o_legacy_toy.active");
            assert.verifySteps([`no state`]);

            await switchView(target, "toy");

            assert.containsOnce(target, ".o_switch_view.o_toy.active");
            assert.verifySteps([`{"locationId":"The place to be"}`]);

            await switchView(target, "legacy_toy");
            await legacyExtraNextTick();

            assert.containsOnce(target, ".o_switch_view.o_legacy_toy.active");
            assert.verifySteps([`{"locationId":"The place to be"}`]);
        }
    );
});
