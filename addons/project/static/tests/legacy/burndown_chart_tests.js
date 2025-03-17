/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { setupControlPanelServiceRegistry, toggleSearchBarMenu, toggleMenuItem, toggleMenuItemOption } from "@web/../tests/search/helpers";
import { makeView } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { getFirstElementForXpath } from './project_test_utils';

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
                            is_closed: {
                                string: "Burn up chart",
                                type: "selection",
                                selection: [['closed', 'Closed tasks'], ['open', 'Open tasks']],
                                store: true,
                                sortable: true
                            },
                            nb_tasks: { string: "Number of Tasks", type: "integer", store: true, sortable: true, aggregator: "sum" }
                        },
                        records: [
                            { id: 1, project_id: 1, stage_id: 1, is_closed: 'open', date: "2020-01-01", nb_tasks: 10 },
                            { id: 2, project_id: 1, stage_id: 2, is_closed: 'open', date: "2020-02-01", nb_tasks: 5 },
                            { id: 3, project_id: 1, stage_id: 3, is_closed: 'closed', date: "2020-03-01", nb_tasks: 2 },
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
                    },
                    "project.task.type": {
                        fields: {
                            name: { string: "Name", type: "char" },
                            sequence: { type: "integer" },
                        },
                    },
                },
                views: {
                    "burndown_chart,false,graph": `
                        <graph type="line" js_class="burndown_chart">
                            <field name="date" string="Date" interval="month"/>
                            <field name="stage_id"/>
                            <field name="is_closed"/>
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
                type: "graph",
            };
            setupControlPanelServiceRegistry();
            const notificationMock = () => {
                assert.step("notification_triggered");
                return () => {};
            };
            registry.category("services").add("notification", makeFakeNotificationService(notificationMock), {
                force: true,
            });
        });

        QUnit.module("BurndownChart");

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
                        <filter string="Stage - Burndown chart" name="stage" context="{'group_by': 'stage_id'}" />
                        <filter string="Is Closed - Burnup chart" name="is_closed" context="{'group_by': 'is_closed'}"/>
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
                        string: "Stage - Burndown chart",
                        type: "many2one",
                        store: true,
                        sortable: true,
                        searchable: true,
                    },
                    is_closed: {
                        name: "is_closed",
                        string: "Is Closed - Burnup chart",
                        type: "selection",
                        store: true,
                        sortable: true,
                        searchable: true,
                    }
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

        async function openGroupByMainMenu(target) {
            await toggleSearchBarMenu(target);
        }

        async function openGroupByDateMenu(target) {
            await openGroupByMainMenu(target);
            await toggleMenuItem(target, 'Date');
        }

        async function toggleGroupByStageMenu(target) {
            await openGroupByMainMenu(target);
            await toggleMenuItem(target, 'Stage - Burndown chart');
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
            const selectedGroupByDateItemElement = getFirstElementForXpath(target, selectedGroupByDateItemXpath);
            await toggleMenuItemOption(target, 'Date', selectedGroupByDateItemElement.innerText);
        }

        QUnit.test("check that removing the group by 'Date: Month > Stage' in the search bar triggers a notification", async function (assert) {

            const stepsTriggeringNotification = async () => {
                // There's only one possibility here
                await click(target, ".o_facet_remove");
            };
            await testBurnDownChartWithSearchView(stepsTriggeringNotification, assert);
        });

        QUnit.test("check that removing the group by 'Date' triggers a notification", async function (assert) {
            const stepsTriggeringNotification = async () => {
                await toggleSelectedGroupByDateItem(target);
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
            const firstNotSelectedGroupByDateItemElement = getFirstElementForXpath(target, firstNotSelectedGroupByDateItemXpath);
            await toggleMenuItemOption(target, 'Date', firstNotSelectedGroupByDateItemElement.innerText);
            const groupByDateSubMenuXpath = `//div
                                            [contains(@class, 'o_group_by_menu')]
                                            //button
                                              [contains(@class, 'o_menu_item')]
                                              [contains(., 'Date')]
                                               /following-sibling::div`;
            const groupByDateSubMenuElement = getFirstElementForXpath(target, groupByDateSubMenuXpath);
            const selectedGroupByDateItemElements = groupByDateSubMenuElement.querySelectorAll('span.o_item_option.selected');
            assert.equal(selectedGroupByDateItemElements.length, 1, 'There is only one selected item.');
            assert.equal(firstNotSelectedGroupByDateItemElement.innerText, selectedGroupByDateItemElements[0].innerText, 'The selected item is the one we clicked on.');
        });

        function checkGroupByOrder(assert) {
            const dateSearchFacetXpath = `//div[contains(@class, 'o_searchview_facet')]
                                            [.//small[contains(@class, 'o_facet_value')]
                                            [contains(., 'Date: Month')]]`;
            const dateSearchFacetElement = getFirstElementForXpath(target, dateSearchFacetXpath);
            const dateSearchFacetParts = dateSearchFacetElement.querySelectorAll('.o_facet_value');
            assert.equal(dateSearchFacetParts.length, 2);
            assert.equal(dateSearchFacetParts[0].innerText, 'Date: Month');
            assert.equal(dateSearchFacetParts[1].innerText, 'Stage - Burndown chart');
        }

        QUnit.test("check that the group by is always sorted 'Date' first, 'Stage' second", async function (assert) {
            await makeBurnDownChartWithSearchView({context: {...makeViewParams.context, 'search_default_date': 1, 'search_default_stage': 1}});
            checkGroupByOrder(assert);
        });

        QUnit.test("check that the group by is always sorted 'Date' first, 'Stage' second", async function (assert) {
            await makeBurnDownChartWithSearchView({context: {...makeViewParams.context, 'search_default_stage': 1, 'search_default_date': 1}});
            checkGroupByOrder(assert);
        });

        function checkGroupByIsClosed(assert) {
            const dateSearchFacetXpath = `//div[contains(@class, 'o_searchview_facet')]
                                            [.//small[contains(@class, 'o_facet_value')]
                                            [contains(., 'Date: Month')]]`;
            const dateSearchFacetElement = getFirstElementForXpath(target, dateSearchFacetXpath);
            const dateSearchFacetParts = dateSearchFacetElement.querySelectorAll('.o_facet_value');
            assert.equal(dateSearchFacetParts.length, 2);
            assert.equal(dateSearchFacetParts[0].innerText, 'Date: Month');
            assert.equal(dateSearchFacetParts[1].innerText, 'Is Closed - Burnup chart');
        }

        QUnit.test("check that the toggle between 'Stage' and 'Burnup chart' are working as intended", async function (assert) {
            await makeBurnDownChartWithSearchView();
            await toggleGroupByStageMenu(target);
            checkGroupByIsClosed(assert);
            await toggleMenuItem(target, 'Is Closed - Burnup chart');
            checkGroupByOrder(assert);
        });
    });
});
