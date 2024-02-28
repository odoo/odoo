/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { registry } from "@web/core/registry";
import { actionService } from "@web/webclient/actions/action_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { spreadsheetLinkMenuCellService } from "@spreadsheet/ir_ui_menu/index";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { selectCell } from "@spreadsheet/../tests/utils/commands";
import { viewService } from "@web/views/view_service";
import { ormService } from "@web/core/orm_service";
import { getMenuServerData } from "@spreadsheet/../tests/links/menu_data_utils";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

const { Model } = spreadsheet;

function beforeEach() {
    registry
        .category("services")
        .add("menu", menuService)
        .add("action", actionService)
        .add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);
    registry.category("services").add("view", viewService, { force: true }); // #action-serv-leg-compat-js-class
    registry.category("services").add("orm", ormService, { force: true }); // #action-serv-leg-compat-js-class
}

QUnit.module("spreadsheet_dashboard > link", { beforeEach });

QUnit.test("click a web link", async (assert) => {
    patchWithCleanup(window, {
        open: (href) => {
            assert.step(href.toString());
        },
    });
    const env = await makeTestEnv();
    const data = {
        sheets: [
            {
                cells: { A1: { content: "[Odoo](https://odoo.com)" } },
            },
        ],
    };
    const model = new Model(data, { mode: "dashboard", evalContext: { env } });
    selectCell(model, "A1");
    assert.verifySteps(["https://odoo.com"]);
});

QUnit.test("click a menu link", async (assert) => {
    const fakeActionService = {
        name: "action",
        start() {
            return {
                doAction(action) {
                    assert.step(action);
                },
            };
        },
    };
    registry.category("services").add("action", fakeActionService, { force: true });
    const env = await makeTestEnv({ serverData: getMenuServerData() });
    const data = {
        sheets: [
            {
                cells: { A1: { content: "[label](odoo://ir_menu_xml_id/test_menu)" } },
            },
        ],
    };
    const model = new Model(data, { mode: "dashboard", evalContext: { env } });
    selectCell(model, "A1");
    assert.verifySteps(["action1"]);
});

QUnit.test("click a menu link", async (assert) => {
    const fakeActionService = {
        name: "action",
        start() {
            return {
                doAction(action) {
                    assert.step("do-action");
                    assert.deepEqual(action, {
                        context: undefined,
                        domain: undefined,
                        name: "an odoo view",
                        res_model: "partner",
                        target: "current",
                        type: "ir.actions.act_window",
                        views: [[false, "list"]],
                    });
                },
            };
        },
    };
    registry.category("services").add("action", fakeActionService, { force: true });
    const env = await makeTestEnv({ serverData: getMenuServerData() });
    const view = {
        name: "an odoo view",
        viewType: "list",
        action: {
            modelName: "partner",
            views: [[false, "list"]],
        },
    };
    const data = {
        sheets: [
            {
                cells: { A1: { content: `[a view](odoo://view/${JSON.stringify(view)})` } },
            },
        ],
    };
    const model = new Model(data, { mode: "dashboard", evalContext: { env } });
    selectCell(model, "A1");
    assert.verifySteps(["do-action"]);
});
