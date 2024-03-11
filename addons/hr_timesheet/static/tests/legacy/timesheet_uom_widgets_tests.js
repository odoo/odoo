/** @odoo-module */

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { companyService } from "@web/webclient/company_service";
import { uiService } from "@web/core/ui/ui_service";
import { makeView, setupViewRegistries} from "@web/../tests/views/helpers";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";

const serviceRegistry = registry.category("services");

QUnit.module("Timesheet UOM Widgets", (hooks) => {
    let serverData;
    let target;
    hooks.beforeEach(async function (assert) {
        setupViewRegistries();
        target = getFixture();
        serverData = {
            models: {
                'account.analytic.line': {
                    fields: {
                        unit_amount: { string: "Unit Amount", type: "float" },
                    },
                    records: [
                        { id: 1, unit_amount: 8 }
                    ],
                },
            },
            views: {
                "account.analytic.line,false,list": `
                    <tree>
                        <field name="unit_amount" widget="timesheet_uom"/>
                    </tree>
                `,
            },
        };
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("company", companyService, { force: true });
        patchWithCleanup(session, {
            user_companies: {
                current_company: 1,
                allowed_companies: {
                    1: {
                        id: 1,
                        name: 'Company',
                        timesheet_uom_id: 2,
                        timesheet_uom_factor: 0.125,
                    },
                },
            },
            user_context: {
                allowed_company_ids: [1],
            },
            uom_ids: {
                1: {
                    id: 1,
                    name: 'hour',
                    rounding: 0.01,
                    timesheet_widget: 'float_time',
                },
                2: {
                    id: 2,
                    name: 'day',
                    rounding: 0.01,
                    timesheet_widget: 'float_toggle',
                },
            }
        });
    });

    QUnit.module("TimesheetFloatToggleField");

    QUnit.test("factor is applied in TimesheetFloatToggleField", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "account.analytic.line",
        });
        assert.containsOnce(target, 'div[name="unit_amount"]:contains("1")', "TimesheetFloatToggleField should take `timesheet_uom_factor` into account");
    });

    QUnit.test("ranges are working properly in TimesheetFloatToggleField", async function (assert) {
        serverData.models["account.analytic.line"].records[0].unit_amount = 1;
        serverData.views["account.analytic.line,false,list"] = serverData.views["account.analytic.line,false,list"].replace('<tree', '<tree editable="bottom"')
        await makeView({
            serverData,
            type: "list",
            resModel: "account.analytic.line",
        });
        // Enter edit mode
        await click(target, 'div[name="unit_amount"]');

        await click(target, 'div[name="unit_amount"] .o_field_float_toggle');
        assert.containsOnce(target, 'div[name="unit_amount"]:contains("0.00")', "ranges are working properly in TimesheetFloatToggleField");
        await click(target, 'div[name="unit_amount"] .o_field_float_toggle');
        assert.containsOnce(target, 'div[name="unit_amount"]:contains("0.50")', "ranges are working properly in TimesheetFloatToggleField");
        await click(target, 'div[name="unit_amount"] .o_field_float_toggle');
        assert.containsOnce(target, 'div[name="unit_amount"]:contains("1.00")', "ranges are working properly in TimesheetFloatToggleField");
    });

    QUnit.module("TimesheetFloatTimeField");

    QUnit.test("factor is applied in TimesheetFloatTimeField", async function (assert) {
        patchWithCleanup(session.user_companies.allowed_companies[1], {timesheet_uom_id: 1});
        await makeView({
            serverData,
            type: "list",
            resModel: "account.analytic.line",
        });
        assert.containsOnce(target, 'div[name="unit_amount"]:contains("08:00")', "TimesheetFloatTimeField should not take `timesheet_uom_factor` into account");
    });

    QUnit.module("TimesheetFloatFactorField");

    QUnit.test("factor is applied in TimesheetFloatFactorField", async function (assert) {
        patchWithCleanup(session.uom_ids[2], {timesheet_widget: 'float_factor'});
        await makeView({
            serverData,
            type: "list",
            resModel: "account.analytic.line",
        });
        assert.containsOnce(target, 'div[name="unit_amount"]:contains("1")', "TimesheetFloatFactorField should take `timesheet_uom_factor` into account");
    });

});
