import { defineDocumentSpreadsheetModels } from "@documents_spreadsheet/../tests/helpers/data";
import {
    createSpreadsheet,
    mockActionService,
} from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { describe, expect, test } from "@odoo/hoot";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { defineModels, models } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");
defineDocumentSpreadsheetModels();

const { topbarMenuRegistry } = spreadsheet.registries;

class DocumentsToDashboardWizard extends models.Model {
    _name = "spreadsheet.document.to.dashboard";
}
defineModels({ DocumentsToDashboardWizard });

test("open wizard action", async () => {
    const { env } = await createSpreadsheet({
        spreadsheetId: 2,
        mockRPC: async function (route, args) {
            if (args.method === "save_spreadsheet_snapshot") {
                return true;
            }
        },
    });
    mockActionService((actionRequest, options) => {
        if (actionRequest.res_model === "spreadsheet.document.to.dashboard") {
            expect.step("open_wizard_action");
            expect(actionRequest).toEqual({
                name: "Name your dashboard and select its section",
                type: "ir.actions.act_window",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                res_model: "spreadsheet.document.to.dashboard",
            });
            expect(options).toEqual({
                additionalContext: {
                    default_document_id: 2,
                    default_name: "My spreadsheet",
                },
            });
        }
    });
    await doMenuAction(topbarMenuRegistry, ["file", "add_document_to_dashboard"], env);
    expect.verifySteps(["open_wizard_action"]);
});

test("document's data is saved when opening wizard", async () => {
    const { env, model } = await createSpreadsheet({
        spreadsheetId: 2,
        mockRPC: async function (route, args) {
            if (args.method === "save_spreadsheet_snapshot") {
                expect.step("save_spreadsheet_snapshot");
                const snapshotData = args.args[1];
                expect(snapshotData.sheets[0].cells.A1.content).toBe("a cell updated");
                return true;
            }
        },
    });
    setCellContent(model, "A1", "a cell updated");
    await doMenuAction(topbarMenuRegistry, ["file", "add_document_to_dashboard"], env);
    expect.verifySteps(["save_spreadsheet_snapshot"]);
});
