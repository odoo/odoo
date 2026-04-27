import { patchWithCleanup, getMockEnv, onRpc, serverState } from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { expect, test, getFixture, describe } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

test("Clicking 'Edit' icon navigates to dashboard edit view", async function () {
    serverState.debug = "1";
    const action = {
        type: "ir.actions.client",
        tag: "action_edit_dashboard",
        params: {
            spreadsheet_id: 1,
        },
    };
    await createSpreadsheetDashboard({
        mockRPC: async function (route, args) {
            if (args.method === "action_edit_dashboard" && args.model === "spreadsheet.dashboard") {
                expect.step("action_edit_dashboard");
                return action;
            }
        },
    });
    const env = getMockEnv();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            expect.step("doAction");
            expect(action.params.spreadsheet_id).toBe(1);
            expect(action.tag).toBe("action_edit_dashboard");
        },
    });
    click(".o_edit_dashboard");
    await animationFrame();
    expect.verifySteps(["action_edit_dashboard", "doAction"]);
});

test("User without edit permissions does not see the 'Edit' option on the dashboard (Debug mode ON)", async function () {
    serverState.debug = "1";
    onRpc("has_group", () => false);
    await createSpreadsheetDashboard();
    expect(".o_edit_dashboard").toHaveCount(0);
});

test("User with edit permissions sees the 'Edit' option on the dashboard (Debug mode ON)", async function () {
    serverState.debug = "1";
    onRpc("has_group", () => true);
    await createSpreadsheetDashboard();
    expect(
        getFixture().querySelector(".o_search_panel_category_value .o_edit_dashboard")
    ).toHaveCount(1);
});

test("User with edit permissions does not see the 'Edit' option on the dashboard (Debug mode OFF)", async function () {
    onRpc("has_group", () => true);
    await createSpreadsheetDashboard();
    expect(".o_edit_dashboard").toHaveCount(0);
});

test("Can edit a non-active dashboard", async function () {
    serverState.debug = "1";

    const action = (spreadsheetId) => ({
        type: "ir.actions.client",
        tag: "action_edit_dashboard",
        params: { spreadsheet_id: spreadsheetId },
    });

    await createSpreadsheetDashboard({
        mockRPC: async function (route, args) {
            if (args.method === "action_edit_dashboard" && args.model === "spreadsheet.dashboard") {
                expect.step("action_edit_dashboard");
                return action(args.args[0]);
            }
        },
    });
    const env = getMockEnv();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            expect.step("doAction");
            expect(action.params.spreadsheet_id).toBe(2);
            expect(action.tag).toBe("action_edit_dashboard");
        },
    });
    click(getFixture().querySelectorAll(".o_edit_dashboard")[1]);
    await animationFrame();
    expect.verifySteps(["action_edit_dashboard", "doAction"]);
});
