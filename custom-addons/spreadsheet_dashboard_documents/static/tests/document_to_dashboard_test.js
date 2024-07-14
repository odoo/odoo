/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { createSpreadsheet } from "@documents_spreadsheet/../tests/spreadsheet_test_utils";
import { registry } from "@web/core/registry";
import { actionService } from "@web/webclient/actions/action_service";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";
import { setCellContent } from "@spreadsheet/../tests/utils/commands";

const { topbarMenuRegistry } = spreadsheet.registries;

function getServerData() {
    const serverData = getBasicServerData();
    serverData.models["spreadsheet.document.to.dashboard"] = {
        fields: {},
        records: [],
    };
    serverData.views["spreadsheet.document.to.dashboard,false,form"] = "<form></form>";
    return serverData;
}

QUnit.module("spreadsheet_dashboard_documents > add document to dashboard");

QUnit.test("open wizard action", async (assert) => {
    const serverData = getServerData();
    registry.category("services").add("actionMain", actionService);
    const fakeActionService = {
        dependencies: ["actionMain"],
        start(env, { actionMain }) {
            return {
                ...actionMain,
                get currentController() {
                    return actionMain.currentController;
                },
                doAction(actionRequest, options) {
                    if (actionRequest.res_model === "spreadsheet.document.to.dashboard") {
                        assert.step("open_wizard_action");
                        assert.deepEqual(actionRequest, {
                            name: "Name your dashboard and select its section",
                            type: "ir.actions.act_window",
                            view_mode: "form",
                            views: [[false, "form"]],
                            target: "new",
                            res_model: "spreadsheet.document.to.dashboard",
                        });
                        assert.deepEqual(options, {
                            additionalContext: {
                                default_document_id: 2,
                                default_name: "",
                            },
                        });
                    }
                    actionMain.doAction(...arguments);
                },
            };
        },
    };
    registry.category("services").add("action", fakeActionService, { force: true });
    const { env } = await createSpreadsheet({
        serverData,
        spreadsheetId: 2,
        mockRPC: async function (route, args) {
            if (args.method === "save_spreadsheet_snapshot") {
                return true;
            }
        },
    });
    await doMenuAction(topbarMenuRegistry, ["file", "add_document_to_dashboard"], env);
    assert.verifySteps(["open_wizard_action"]);
});

QUnit.test("document's data is saved when opening wizard", async (assert) => {
    const serverData = getServerData();
    registry.category("services").add("actionMain", actionService);
    const { env, model } = await createSpreadsheet({
        serverData,
        spreadsheetId: 2,
        mockRPC: async function (route, args) {
            if (args.method === "save_spreadsheet_snapshot") {
                assert.step("save_spreadsheet_snapshot");
                const snapshotData = args.args[1];
                assert.strictEqual(snapshotData.sheets[0].cells.A1.content, "a cell updated");
                return true;
            }
        },
    });
    setCellContent(model, "A1", "a cell updated");
    await doMenuAction(topbarMenuRegistry, ["file", "add_document_to_dashboard"], env);
    assert.verifySteps(["save_spreadsheet_snapshot"]);
});
