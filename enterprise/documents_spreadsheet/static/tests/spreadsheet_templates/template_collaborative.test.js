import { defineDocumentSpreadsheetModels } from "@documents_spreadsheet/../tests/helpers/data";
import {
    createSpreadsheetTemplate,
    displayedConnectedUsers,
    getConnectedUsersElImage,
    getSynchedStatus,
} from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import {
    joinSession,
    leaveSession,
} from "@spreadsheet_edition/../tests/helpers/collaborative_helpers";
import { mockService } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

defineDocumentSpreadsheetModels();

test("Number of connected users is correctly rendered", async function () {
    const { transportService } = await createSpreadsheetTemplate();
    expect(displayedConnectedUsers()).toBe(1, {
        message: "It should display one connected user",
    });
    expect(getConnectedUsersElImage()).toHaveClass("fa-user", {
        message: "It should display the fa-user icon",
    });
    joinSession(transportService, { id: 1234, userId: 9999 });
    await animationFrame();
    expect(displayedConnectedUsers()).toBe(2, {
        message: "It should display two connected users",
    });
    expect(getConnectedUsersElImage()).toHaveClass("fa-users", {
        message: "It should display the fa-users icon",
    });

    // The same user is connected with two different tabs.
    joinSession(transportService, { id: 4321, userId: 9999 });
    await animationFrame();
    expect(displayedConnectedUsers()).toBe(2, {
        message: "It should display two connected users",
    });

    leaveSession(transportService, 4321);
    await animationFrame();
    expect(displayedConnectedUsers()).toBe(2, {
        message: "It should display two connected users",
    });

    leaveSession(transportService, 1234);
    await animationFrame();
    expect(displayedConnectedUsers()).toBe(1, {
        message: "It should display one connected user",
    });
});

test("collaborative session client has the user id", async function () {
    const { model } = await createSpreadsheetTemplate();
    const clients = [...model.getters.getConnectedClients()];
    expect(clients.length).toBe(1);
    const localClient = clients[0];
    expect(localClient.name).toBe("Mitchell Admin");
    expect(localClient.userId).toBe(user.userId);
});

test("Sync status is correctly rendered", async function () {
    const { model, transportService } = await createSpreadsheetTemplate();
    await animationFrame();
    expect(getSynchedStatus()).toBe("Saved");
    await transportService.concurrent(async () => {
        setCellContent(model, "A1", "hello");
        await animationFrame();
        expect(getSynchedStatus()).toBe("Saving");
    });
    await animationFrame();
    expect(getSynchedStatus()).toBe("Saved");
});

test("receiving bad revision reload", async function () {
    mockService("action", {
        doAction(actionRequest) {
            if (actionRequest === "reload_context") {
                expect.step("reload");
            } else {
                return super.doAction(...arguments);
            }
        },
    });
    const { transportService } = await createSpreadsheetTemplate();
    transportService.broadcast({
        type: "REMOTE_REVISION",
        serverRevisionId: "an invalid revision id",
        nextRevisionId: "the next revision id",
        revision: {},
    });
    expect.verifySteps(["reload"]);
});
