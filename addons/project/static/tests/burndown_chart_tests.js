/** @odoo-module alias=project.BurndownView */
import { dom, createView, nextTick } from 'web.test_utils';
import { COLORS, hexToRGBA } from 'web/static/src/js/views/graph/graph_utils';
import { BurndownChartView } from '../src/js/burndown_chart/view';

QUnit.module('Project', {}, function () {
    QUnit.module('Views', {
        beforeEach() {
            this.data = {
                burndown_chart: {
                    fields: {
                        date: { string: "Date", type: 'date', store: true, sortable: true },
                        project_id: { string: "Project", type: "many2one", relation: 'project', store: true },
                        stage_id: { string: "Stage", type: "many2one", relation: 'stage', store: true },
                        nb_tasks: { string: "Number of Tasks", type: 'integer', store: true }
                    },
                    records: [
                        { id: 1, project_id: 1, stage_id: 1, date: "2020-01-01", nb_tasks: 10 },
                        { id: 2, project_id: 1, stage_id: 2, date: "2020-02-01", nb_tasks: 5 },
                        { id: 3, project_id: 1, stage_id: 3, date: "2020-03-01", nb_tasks: 2 },
                    ],
                },
                project: {
                    fields: {
                        name: { string: 'Project Name', type: "char" },
                    },
                    records: [
                        { id: 1, name: 'Project A' },
                    ]
                },
                stage: {
                    fields: {
                        name: {string: 'Stage Name', type: 'char' },
                    },
                    records: [
                        { id: 1, name: 'Todo' },
                        { id: 2, name: 'In Progress' },
                        { id: 3, name: 'Done' },
                    ]
                }
            };

            this.burndown_chart = {
                View: BurndownChartView,
                model: 'burndown_chart',
                data: this.data,
                arch: `<graph type="line">
                    <field name="date" string="Date" interval="month" type="row"/>
                    <field name="stage_id"/>
                    <field name="nb_tasks" type="measure"/>
                </graph>`,
            };
        }
    }, function () {
        QUnit.module('BurndownChart');

        QUnit.test('check if default mode is line chart and line chart is stacked for burndown chart', async function (assert) {
            assert.expect(5);

            const burndown_chart = await createView(this.burndown_chart);

            assert.strictEqual(burndown_chart.renderer.props.mode, "line", "should be in line chart mode by default.");
            assert.ok(burndown_chart.renderer.props.stacked, "should be stacked by default.");

            assert.ok(burndown_chart.renderer.componentRef.comp._getScaleOptions().yAxes.every(y => y.stacked), "the stacked property in y axes should be true when the stacked is enabled in line chart");
            assert.ok(burndown_chart.renderer.componentRef.comp._getElementOptions().line.fill, "The fill property should be true to add backgroundColor in line chart.");

            const actualDatasets = [];
            const expectedDatasets = [];
            const keysToEvaluate = ['backgroundColor', 'borderColor', 'originIndex', 'pointBackgroundColor'];
            const datasets = burndown_chart.renderer.componentRef.comp.chart.data.datasets;

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

            burndown_chart.destroy();
        });

        QUnit.test('check if the stacked button is visible in the line chart', async function (assert) {
            assert.expect(3);

            const burndown_chart = await createView(this.burndown_chart);

            assert.containsN(burndown_chart, '.o_graph_button[data-mode="stack"]', 1, "should find the stacked button in the controller of the view.");
            const $stackButton = burndown_chart.$buttons.find('.o_graph_button[data-mode="stack"]');
            assert.doesNotHaveClass($stackButton, 'o_hidden', "the stacked button should not have the .o_hidden class when we are in the line chart.");

            await dom.click($stackButton);
            assert.notOk(burndown_chart.renderer.props.stacked, "should be disabled and display a classic line chart.");

            burndown_chart.destroy();
        });

        QUnit.test('check if it is classic line chart when stacked prop is false in line chart', async function (assert) {
            assert.expect(4);

            const burndown_chart = await createView(this.burndown_chart);

            const $stackButton = burndown_chart.$buttons.find('.o_graph_button[data-mode="stack"]');
            await dom.click($stackButton);
            assert.notOk(burndown_chart.renderer.props.stacked, "should be disabled and display a classic line chart.");

            assert.notOk(burndown_chart.renderer.componentRef.comp._getScaleOptions().yAxes.every(y => y.stacked), "the y axes should have a stacked property set to false since the stacked property in line chart is false.");
            assert.notOk(burndown_chart.renderer.componentRef.comp._getElementOptions().line.fill, "The fill property should be false since the stacked property is false.");

            const actualDatasets = [];
            const expectedDatasets = [];
            const keysToEvaluate = ['backgroundColor', 'borderColor', 'originIndex', 'pointBackgroundColor'];
            const datasets = burndown_chart.renderer.componentRef.comp.chart.data.datasets;

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

            burndown_chart.destroy();
        });
    });
});
