/** @odoo-module */

import { selectCell, setCellContent } from "@spreadsheet/../tests/utils/commands";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getAccountingData } from "../accounting_test_data";
import {
    createModelWithDataSource,
    waitForDataSourcesLoaded,
} from "@spreadsheet/../tests/utils/model";
import { registry } from "@web/core/registry";

const { cellMenuRegistry } = spreadsheet.registries;

let serverData;

function beforeEach() {
    serverData = getAccountingData();
}

QUnit.module("spreadsheet_account > Accounting Drill down", { beforeEach }, () => {
    QUnit.test("Create drill down domain", async (assert) => {
        const drillDownAction = {
            type: "ir.actions.act_window",
            res_model: "account.move.line",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: [["account_id", "in", [1, 2]]],
            name: "my awesome action",
        };
        const fakeActionService = {
            name: "action",
            start() {
                return {
                    async doAction(action, options) {
                        assert.step("drill down action");
                        assert.deepEqual(action, drillDownAction);
                        assert.equal(options, undefined);
                        return true;
                    },
                };
            },
        };
        registry.category("services").add("action", fakeActionService, { force: true });

        const model = await createModelWithDataSource({
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_move_line_action") {
                    assert.deepEqual(args.args, [
                        {
                            code: "100",
                            company_id: null,
                            include_unposted: false,
                            date_range: {
                                range_type: "year",
                                year: 2020,
                            },
                        },
                    ]);
                    return drillDownAction;
                }
            },
        });
        const env = model.config.evalContext.env;
        env.model = model;
        setCellContent(model, "A1", `=ODOO.BALANCE("100", 2020)`);
        setCellContent(model, "A2", `=ODOO.BALANCE("100", 0)`);
        await waitForDataSourcesLoaded(model);
        selectCell(model, "A1");
        const root = cellMenuRegistry.getAll().find((item) => item.id === "move_lines_see_records");
        assert.equal(root.isVisible(env), true);
        await root.action(env);
        assert.verifySteps(["drill down action"]);
        selectCell(model, "A2");
        assert.equal(root.isVisible(env), false);
    });
});
