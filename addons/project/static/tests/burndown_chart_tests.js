/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { setupControlPanelServiceRegistry, toggleGroupByMenu, toggleMenuItem, toggleMenuItemOption } from "@web/../tests/search/helpers";
import { COLORS, hexToRGBA } from "@web/views/graph/colors";
import { dialogService } from "@web/core/dialog/dialog_service";
import { getGraphRenderer } from "@web/../tests/views/graph_view_tests";
import { makeView } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";

const serviceRegistry = registry.category("services");
QUnit.module("Project", {}, () => {
    QUnit.module("Views", (hooks) => {
        let makeViewParams;
        let target;
        hooks.beforeEach(async (assert) => {
            target = getFixture();
            const serverData = {
                models: {
                    burndown_chart: {
                        fields: {
                            date: { string: "Date", type: "date", store: true, sortable: true },
                            project_id: { string: "Project", type: "many2one", relation: "project", store: true, sortable: true },
                            stage_id: { string: "Stage", type: "many2one", relation: "stage", store: true, sortable: true },
                            nb_tasks: { string: "Number of Tasks", type: "integer", store: true, sortable: true, group_operator: "sum" }
                        },
                        records: [
                            { id: 1, project_id: 1, stage_id: 1, date: "2020-01-01", nb_tasks: 10 },
                            { id: 2, project_id: 1, stage_id: 2, date: "2020-02-01", nb_tasks: 5 },
                            { id: 3, project_id: 1, stage_id: 3, date: "2020-03-01", nb_tasks: 2 },
                        ],
                    },
                    project: {
                        fields: {
                            name: { string: "Project Name", type: "char" },
                        },
                        records: [{ id: 1, name: "Project A" }]
                    },
                    stage: {
                        fields: {
                            name: { string: "Stage Name", type: "char" },
                        },
                        records: [
                            { id: 1, name: "Todo" },
                            { id: 2, name: "In Progress" },
                            { id: 3, name: "Done" },
                        ],
                    }
                },
                views: {
                    "burndown_chart,false,graph": `
                        <graph type="line">
                            <field name="date" string="Date" interval="month"/>
                            <field name="stage_id"/>
                            <field name="nb_tasks" type="measure"/>
                        </graph>
                    `,
                    "burndown_chart,false,search": `
                        <search/>
                    `,
                },
            };
            makeViewParams = {
                serverData,
                resModel: "burndown_chart",
                type: "burndown_chart",
            };
            setupControlPanelServiceRegistry();
            const notificationMock = () => {
                assert.step("notification_triggered");
                return () => {};
            };
            registry.category("services").add("notification", makeFakeNotificationService(notificationMock), {
                force: true,
            });
            serviceRegistry.add("dialog", dialogService);
        });

        QUnit.module("BurndownChart");

        QUnit.test("check if default mode is line chart and line chart is stacked for burndown chart", async function (assert) {
            assert.expect(5);

            const burndownChart = await makeView(makeViewParams);

            assert.strictEqual(burndownChart.model.metaData.mode, "line", "should be in line chart mode.");
            assert.ok(burndownChart.model.metaData.stacked, "should be stacked by default.");

            assert.ok(getGraphRenderer(burndownChart).getScaleOptions().yAxes.every(y => y.stacked), "the stacked property in y axes should be true when the stacked is enabled in line chart");
            assert.ok(getGraphRenderer(burndownChart).getElementOptions().line.fill, "The fill property should be true to add backgroundColor in line chart.");

            const actualDatasets = [];
            const expectedDatasets = [];
            const keysToEvaluate = ["backgroundColor", "borderColor", "originIndex", "pointBackgroundColor"];
            const datasets = getGraphRenderer(burndownChart).chart.data.datasets;

            for (let i = 0; i < datasets.length; i++) {
                const dataset = datasets[i];
                const actualDataset = {};
                keysToEvaluate.forEach(key => {
                    if (dataset.hasOwnProperty(key)) {
                        actualDataset[key] = dataset[key];
                    }
                });
                actualDatasets.push(actualDataset);

                const expectedColor = COLORS[i];
                expectedDatasets.push({
                    backgroundColor: hexToRGBA(expectedColor, 0.4),
                    borderColor: expectedColor,
                    originIndex: 0,
                    pointBackgroundColor: expectedColor,
                });
            }
            assert.deepEqual(actualDatasets, expectedDatasets);
        });

        QUnit.test("check if the stacked button is visible in the line chart", async function (assert) {
            assert.expect(3);
            const burndownChart = await makeView(makeViewParams);
            assert.ok(burndownChart.model.metaData.stacked, "graph should be a burndown chart.");
            assert.containsOnce(target, `button.o_graph_button[data-tooltip="Stacked"]`);
            const stackButton = target.querySelector(`button.o_graph_button[data-tooltip="Stacked"]`);
            await click(stackButton);
            assert.notOk(burndownChart.model.metaData.stacked, "graph should be a classic line chart.");
        });

        QUnit.test("check if it is classic line chart when stacked prop is false in line chart", async function (assert) {
            assert.expect(4);

            const burndownChart = await makeView(makeViewParams);

            const stackButton = target.querySelector(`button.o_graph_button[data-tooltip="Stacked"]`);
            await click(stackButton);
            assert.notOk(burndownChart.model.metaData.stacked, "graph should be a classic line chart.");

            assert.notOk(getGraphRenderer(burndownChart).getScaleOptions().yAxes.every(y => y.stacked), "the y axes should have a stacked property set to false since the stacked property in line chart is false.");
            assert.notOk(getGraphRenderer(burndownChart).getElementOptions().line.fill, "The fill property should be false since the stacked property is false.");

            const actualDatasets = [];
            const expectedDatasets = [];
            const keysToEvaluate = ["backgroundColor", "borderColor", "originIndex", "pointBackgroundColor"];
            const datasets = getGraphRenderer(burndownChart).chart.data.datasets;

            for (let i = 0; i < datasets.length; i++) {
                const dataset = datasets[i];
                const actualDataset = {};
                keysToEvaluate.forEach(key => {
                    if (dataset.hasOwnProperty(key)) {
                        actualDataset[key] = dataset[key];
                    }
                });
                actualDatasets.push(actualDataset);

                const expectedColor = COLORS[i];
                expectedDatasets.push({
                    borderColor: expectedColor,
                    originIndex: 0,
                    pointBackgroundColor: expectedColor,
                });
            }

            assert.deepEqual(actualDatasets, expectedDatasets);
        });

        QUnit.test("check that the sort buttons are invisible", async function (assert) {
            await makeView(makeViewParams);
            assert.containsNone(target, '.o_cp_bottom_left:has(.btn-group[role=toolbar][aria-label="Sort graph"])', "The sort buttons are not rendered.");
        });

        async function makeBurnDownChartWithSearchView(makeViewOverwriteParams = { }) {
            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
                clearTimeout: () => {},
            });
            await makeView({
                ...makeViewParams,
                searchViewId: false,
                searchViewArch: `
                    <search string="Burndown Chart">
                        <filter string="Date" name="date" context="{'group_by': 'date'}" />
                        <filter string="Stage" name="stage" context="{'group_by': 'stage_id'}" />
                    </search>
                `,
                searchViewFields: {
                    date: {
                        name: "date",
                        string: "Date",
                        type: "date",
                        store: true,
                        sortable: true,
                        searchable: true,
                    },
                    stage_id: {
                        name: "stage_id",
                        string: "Stage",
                        type: "many2one",
                        store: true,
                        sortable: true,
                        searchable: true,
                    },
                },
                context: { ...makeViewParams.context, 'search_default_date': 1, 'search_default_stage': 1 },
                ...makeViewOverwriteParams,
            });
        }

        async function testBurnDownChartWithSearchView(stepsTriggeringNotification, assert) {
            await makeBurnDownChartWithSearchView();
            await stepsTriggeringNotification();
            assert.verifySteps(['notification_triggered']);
        }

        function getFirstElementForXpath(xpath) {
            const xPathResult = document.evaluate(xpath, target, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
            return xPathResult.singleNodeValue;
        }

        async function openGroupByMainMenu(target) {
            await toggleGroupByMenu(target);
        }

        async function openGroupByDateMenu(target) {
            await openGroupByMainMenu(target);
            await toggleMenuItem(target, 'Date');
        }

        async function toggleGroupByStageMenu(target) {
            await openGroupByMainMenu(target);
            await toggleMenuItem(target, 'Stage');
        }

        async function toggleSelectedGroupByDateItem(target) {
            await openGroupByDateMenu(target);
            const selectedGroupByDateItemXpath = `//div
                                                    [contains(@class, 'o_group_by_menu')]
                                                    //button
                                                      [contains(@class, 'o_menu_item')]
                                                      [contains(., 'Date')]
                                                       /following-sibling::div
                                                         /span
                                                          [contains(@class, 'o_item_option')]
                                                          [contains(@class, 'selected')]`;
            const selectedGroupByDateItemElement = getFirstElementForXpath(selectedGroupByDateItemXpath);
            await toggleMenuItemOption(target, 'Date', selectedGroupByDateItemElement.innerText);
        }

        QUnit.test("check that removing the group by 'Date: Month > Stage' in the search bar triggers a notification", async function (assert) {

            const stepsTriggeringNotification = async () => {
                const removeFilterXpath = `//div[contains(@class, 'o_searchview_facet')]
                                                [.//span[@class='o_facet_value']
                                                [contains(., 'Date: Month')]]
                                            /i[contains(@class, 'o_facet_remove')]`;
                const removeFilterElement = getFirstElementForXpath(removeFilterXpath);
                await click(removeFilterElement);
            };
            await testBurnDownChartWithSearchView(stepsTriggeringNotification, assert);
        });

        QUnit.test("check that removing the group by 'Date' triggers a notification", async function (assert) {
            const stepsTriggeringNotification = async () => {
                await toggleSelectedGroupByDateItem(target);
            };
            await testBurnDownChartWithSearchView(stepsTriggeringNotification, assert);
        });

        QUnit.test("check that removing the group by 'Stage' triggers a notification", async function (assert) {
            const stepsTriggeringNotification = async () => {
                await toggleGroupByStageMenu(target);
            };
            await testBurnDownChartWithSearchView(stepsTriggeringNotification, assert);
        });

        QUnit.test("check that adding a group by 'Date' actually toggle it", async function (assert) {
            await makeBurnDownChartWithSearchView();
            await openGroupByDateMenu(target);
            const firstNotSelectedGroupByDateItemXpath = `//div
                                    [contains(@class, 'o_group_by_menu')]
                                    //button
                                      [contains(@class, 'o_menu_item')]
                                      [contains(., 'Date')]
                                       /following-sibling::div
                                         /span
                                          [contains(@class, 'o_item_option')]
                                          [not(contains(@class, 'selected'))]`;
            const firstNotSelectedGroupByDateItemElement = getFirstElementForXpath(firstNotSelectedGroupByDateItemXpath);
            await toggleMenuItemOption(target, 'Date', firstNotSelectedGroupByDateItemElement.innerText);
            const groupByDateSubMenuXpath = `//div
                                            [contains(@class, 'o_group_by_menu')]
                                            //button
                                              [contains(@class, 'o_menu_item')]
                                              [contains(., 'Date')]
                                               /following-sibling::div`;
            const groupByDateSubMenuElement = getFirstElementForXpath(groupByDateSubMenuXpath);
            const selectedGroupByDateItemElements = groupByDateSubMenuElement.querySelectorAll('span.o_item_option.selected');
            assert.equal(selectedGroupByDateItemElements.length, 1, 'There is only one selected item.');
            assert.equal(firstNotSelectedGroupByDateItemElement.innerText, selectedGroupByDateItemElements[0].innerText, 'The selected item is the one we clicked on.');
        });

        function checkGroupByOrder(assert) {
            const dateSearchFacetXpath = `//div[contains(@class, 'o_searchview_facet')]
                                            [.//span[@class='o_facet_value']
                                            [contains(., 'Date: Month')]]`;
            const dateSearchFacetElement = getFirstElementForXpath(dateSearchFacetXpath);
            const dateSearchFacetParts = dateSearchFacetElement.querySelectorAll('.o_facet_value');
            assert.equal(dateSearchFacetParts.length, 2);
            assert.equal(dateSearchFacetParts[0].innerText, 'Date: Month');
            assert.equal(dateSearchFacetParts[1].innerText, 'Stage');
        }

        QUnit.test("check that the group by is always sorted 'Date' first, 'Stage' second", async function (assert) {
            await makeBurnDownChartWithSearchView({context: {...makeViewParams.context, 'search_default_date': 1, 'search_default_stage': 1}});
            checkGroupByOrder(assert);
        });

        QUnit.test("check that the group by is always sorted 'Date' first, 'Stage' second", async function (assert) {
            await makeBurnDownChartWithSearchView({context: {...makeViewParams.context, 'search_default_stage': 1, 'search_default_date': 1}});
            checkGroupByOrder(assert);
        });
    });
});
