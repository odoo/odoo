odoo.define('hr_timesheet.timesheet_graph_tests', function (require) {
"use strict";

const session = require('web.session');
const SetupTimesheetUOMWidgetsTestEnvironment = require('hr_timesheet.timesheet_uom_tests_env');
const GraphView = require('hr_timesheet.GraphView');

QUnit.module('Timesheet UOM Widgets', function (hooks) {
    let env;
    let sessionUserCompaniesBackup;
    let sessionUserContextBackup;
    let sessionUOMIdsBackup;
    let sessionUIDBackup;
    hooks.before(function (assert) {
        env = new SetupTimesheetUOMWidgetsTestEnvironment();
        // Backups session parts that this testing module will alter in order to restore it at the end.
        sessionUserCompaniesBackup = session.user_companies || false;
        sessionUserContextBackup = session.user_context || false;
        sessionUOMIdsBackup = session.uom_ids || false;
        sessionUIDBackup = session.uid || false;
    });
    hooks.after(function (assert) {
        // Restores the session
        const sessionToApply = Object.assign(
            { },
            sessionUserCompaniesBackup && {
                user_companies: sessionUserCompaniesBackup,
            } || { },
            sessionUserContextBackup && {
                user_context: sessionUserContextBackup,
            } || { },
            sessionUOMIdsBackup && {
                uom_ids: sessionUOMIdsBackup,
            } || { },
            sessionUIDBackup && {
                uid: sessionUIDBackup,
            } || { });
        env.triggerAbstractWebClientInit(sessionToApply, true);
    });
    QUnit.module('GraphView', function (hooks) {
        QUnit.test('the timesheet_graph view data are multiplied by a factor that is company related', async function (assert) {
            assert.expect(2);

            let options = {
                View: GraphView,
                arch: '<graph><field name="unit_amount"/></graph>',
                viewOptions: {
                    context: {
                        graph_measure: 'unit_amount',
                    },
                },
            };
            let graph = await env.createView(options);
            let renderedData = graph.renderer.componentRef.comp.chart.data.datasets[0].data[0];
            assert.strictEqual(renderedData, 8, 'The timesheet_graph is taking the timesheet_uom_factor into account');
            graph.destroy();

            options = Object.assign(
                { },
                options,
                {
                    session: {
                        user_context: env.singleCompanyDayUOMUser,
                    },
                });
            graph = await env.createView(options);
            renderedData = graph.renderer.componentRef.comp.chart.data.datasets[0].data[0];
            assert.strictEqual(renderedData, 1, 'The timesheet_graph is taking the timesheet_uom_factor into account');
            graph.destroy();
        });
    });
});
});
