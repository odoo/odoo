/** @odoo-module */

import { selectCell, setCellContent } from "@spreadsheet/../tests/utils/commands";
import * as spreadsheet from "@odoo/o-spreadsheet";
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
                            codes: ["100"],
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
        const env = model.config.custom.env;
        env.model = model;
        setCellContent(model, "A1", `=ODOO.BALANCE("100", 2020)`);
        setCellContent(model, "A2", `=ODOO.BALANCE("100", 0)`);
        setCellContent(model, "A3", `=ODOO.BALANCE("100", 2020, , , FALSE)`);
        setCellContent(model, "A4", `=ODOO.BALANCE("100", 2020, , , )`);
        // Does not affect non formula cells
        setCellContent(model, "A5", `5`);
        await waitForDataSourcesLoaded(model);
        selectCell(model, "A1");
        const root = cellMenuRegistry
            .getMenuItems()
            .find((item) => item.id === "move_lines_see_records");
        assert.equal(root.isVisible(env), true);
        await root.execute(env);
        assert.verifySteps(["drill down action"]);
        selectCell(model, "A2");
        assert.equal(root.isVisible(env), false);
        selectCell(model, "A3");
        assert.equal(root.isVisible(env), true);
        await root.execute(env);
        assert.verifySteps(["drill down action"]);
        selectCell(model, "A4");
        assert.equal(root.isVisible(env), true);
        await root.execute(env);
        assert.verifySteps(["drill down action"]);
        selectCell(model, "A5");
        assert.equal(root.isVisible(env), false);
    });
});
