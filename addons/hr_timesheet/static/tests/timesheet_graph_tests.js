/** @odoo-module **/

import { companyService } from "@web/webclient/company_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { getGraphRenderer } from "@web/../tests/views/graph_view_tests";
import { makeView } from "@web/../tests/views/helpers";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";

const serviceRegistry = registry.category("services");

QUnit.module('hr_timesheet', function (hooks) {
    let serverData;
    hooks.beforeEach(() => {
        serverData = {
            models: {
                'account.analytic.line': {
                    fields: {
                        unit_amount: { string: "Unit Amount", type: "float", group_operator: "sum", store: true },
                    },
                    records: [
                        { id: 1, unit_amount: 8 }
                    ],
                },
            },
            views: {
                // unit_amount is used as group_by and measure
                "account.analytic.line,false,graph": `
                    <graph>
                        <field name="unit_amount"/>
                        <field name="unit_amount" type="measure"/>
                    </graph>
                `,
            }
        }
        setupControlPanelServiceRegistry();
        serviceRegistry.add("company", companyService, { force: true });
        serviceRegistry.add("dialog", dialogService);
    });

    QUnit.module("hr_timesheet_graphview");

    QUnit.test('the timesheet graph view data are not multiplied by a factor that is company related (factor = 1)', async function (assert) {
        assert.expect(1);

        patchWithCleanup(session.user_companies.allowed_companies[1], {
            timesheet_uom_factor: 1,
        });

        const graph = await makeView({
            serverData,
            resModel: "account.analytic.line",
            type: "hr_timesheet_graphview",
        });

        const renderedData = getGraphRenderer(graph).chart.data.datasets[0].data;
        assert.deepEqual(renderedData, [8], 'The timesheet graph view is taking the timesheet_uom_factor into account (factor === 1)');
    });

    QUnit.test('the timesheet graph view data are multiplied by a factor that is company related (factor !== 1)', async function (assert) {
        assert.expect(1);

        patchWithCleanup(session.user_companies.allowed_companies[1], {
            timesheet_uom_factor: 0.125,
        });

        const graph = await makeView({
            serverData,
            resModel: "account.analytic.line",
            type: "hr_timesheet_graphview",
        });

        const renderedData = getGraphRenderer(graph).chart.data.datasets[0].data;
        assert.deepEqual(renderedData, [1], 'The timesheet graph view is taking the timesheet_uom_factor into account (factor !== 1)');
    });
});
