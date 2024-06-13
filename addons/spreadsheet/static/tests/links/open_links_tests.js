/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { registry } from "@web/core/registry";
import { actionService } from "@web/webclient/actions/action_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { spreadsheetLinkMenuCellService } from "@spreadsheet/ir_ui_menu/index";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getMenuServerData } from "@spreadsheet/../tests/links/menu_data_utils";
import { patchWithCleanup, nextTick } from "@web/../tests/helpers/utils";
import { getEvaluatedCell } from "../utils/getters";
import { setCellContent } from "@spreadsheet/../tests/utils/commands";

const { Model } = spreadsheet;
const { urlRepresentation, openLink } = spreadsheet.links;

function beforeEach() {
    registry
        .category("services")
        .add("menu", menuService)
        .add("action", actionService)
        .add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);
}

QUnit.module("spreadsheet > link", { beforeEach });

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
    const model = new Model(data, { custom: { env } });
    const cell = getEvaluatedCell(model, "A1");
    assert.strictEqual(urlRepresentation(cell.link, model.getters), "https://odoo.com");
    openLink(cell.link, env);
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
    const model = new Model(data, { custom: { env } });
    const cell = getEvaluatedCell(model, "A1");
    assert.strictEqual(urlRepresentation(cell.link, model.getters), "menu with xmlid");
    openLink(cell.link, env);
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

    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", `[a view](odoo://view/${JSON.stringify(view)})`);
    const cell = getEvaluatedCell(model, "A1");
    assert.strictEqual(urlRepresentation(cell.link, model.getters), "an odoo view");
    openLink(cell.link, env);
    assert.verifySteps(["do-action"]);
});

QUnit.test("Click a link containing an action xml id", async (assert) => {
    const env = await makeTestEnv({ serverData: getMenuServerData() });
    env.services.action = {
        ...env.services.action,
        doAction(action) {
            assert.step("do-action");
            assert.equal(action.name, "My Action Name");
            assert.equal(action.res_model, "ir.ui.menu");
            assert.equal(action.target, "current");
            assert.equal(action.type, "ir.actions.act_window");
            assert.deepEqual(action.views, [[1, "list"]]);
            assert.deepEqual(action.domain, [(1, "=", 1)]);
        },
    };

    const view = {
        name: "My Action Name",
        viewType: "list",
        action: {
            modelName: "ir.ui.menu",
            views: [[false, "list"]],
            domain: [(1, "=", 1)],
            xmlId: "spreadsheet.action1",
        },
    };

    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", `[an action link](odoo://view/${JSON.stringify(view)})`);
    const cell = getEvaluatedCell(model, "A1");
    assert.strictEqual(urlRepresentation(cell.link, model.getters), "My Action Name");
    await openLink(cell.link, env);
    await nextTick();
    assert.verifySteps(["do-action"]);
});

QUnit.test("Can open link when some views are absent from the referred action", async (assert) => {
    const env = await makeTestEnv({ serverData: getMenuServerData() });
    env.services.action = {
        ...env.services.action,
        doAction(action) {
            assert.step("do-action");
            assert.equal(action.name, "My Action Name");
            assert.equal(action.res_model, "ir.ui.menu");
            assert.equal(action.target, "current");
            assert.equal(action.type, "ir.actions.act_window");
            assert.deepEqual(action.views, [
                [false, "list"],
                [false, "form"],
            ]);
            assert.deepEqual(action.domain, [(1, "=", 1)]);
        },
    };

    const view = {
        name: "My Action Name",
        viewType: "list",
        action: {
            modelName: "ir.ui.menu",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [(1, "=", 1)],
            xmlId: "spreadsheet.action2",
        },
    };

    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", `[an action link](odoo://view/${JSON.stringify(view)})`);
    const cell = getEvaluatedCell(model, "A1");
    assert.strictEqual(urlRepresentation(cell.link, model.getters), "My Action Name");
    await openLink(cell.link, env);
    await nextTick();
    assert.verifySteps(["do-action"]);
});
