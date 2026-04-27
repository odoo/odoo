/** @odoo-module */

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { getFixture, patchDate } from "@web/../tests/helpers/utils";

let serverData, target;

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                "account.analytic.line": {
                    fields: {
                        account_id: {
                            string: "Analytic Account",
                            type: "many2one",
                            relation: "account.analytic",
                        },
                        date: { string: "Date", type: "date" },
                        unit_amount: {
                            string: "Unit Amount",
                            type: "float",
                            aggregator: "sum",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            account_id: 31,
                            date: "2017-01-24",
                            unit_amount: 2.5,
                        },
                        {
                            id: 2,
                            account_id: 31,
                            date: "2017-01-25",
                            unit_amount: 2,
                        },
                        {
                            id: 3,
                            account_id: 31,
                            date: "2017-01-25",
                            unit_amount: 5.5,
                        },
                        {
                            id: 4,
                            account_id: 31,
                            date: "2017-01-30",
                            unit_amount: 10,
                        },
                        {
                            id: 5,
                            account_id: 142,
                            date: "2017-01-31",
                            unit_amount: -3.5,
                        },
                    ],
                },
                "account.analytic": {
                    fields: {
                        name: { string: "Analytic Account Name", type: "char" },
                    },
                    records: [
                        { id: 31, display_name: "P1" },
                        { id: 142, display_name: "Webocalypse Now" },
                    ],
                },
            },
            views: {
                "account.analytic.line,false,grid": `
                    <grid js_class="analytic_line_grid">
                        <field name="account_id" type="row"/>
                        <field name="date" type="col">
                            <range name="year" string="Year" span="year" step="month"/>
                            <range name="month" string="Month" span="month" step="day"/>
                        </field>
                        <field name="unit_amount" type="measure" widget="float_time"/>
                    </grid>`,
            },
        };
        setupViewRegistries();
        target = getFixture();
        patchDate(2017, 0, 30, 0, 0, 0);
    });

    QUnit.module("AnalyticLineGrid");

    QUnit.test("display right period on grid view in year range", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "account.analytic.line",
            serverData,
            viewId: false,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                } else if (args.method === "grid_compute_year_range") {
                    return {
                        date_from: "2016-05-01",
                        date_to: "2017-04-30",
                    };
                }
            },
        });

        const columns = target.querySelectorAll(
            ".o_grid_column_title:not(.o_grid_row_total,.o_grid_navigation_wrap)"
        );
        assert.strictEqual(
            columns.length,
            12,
            "12 columns should be rendered to display 12 months"
        );
        assert.strictEqual(columns[0].textContent, "May\n2016");
        assert.strictEqual(columns[columns.length - 1].textContent, "April\n2017");
    });
});
