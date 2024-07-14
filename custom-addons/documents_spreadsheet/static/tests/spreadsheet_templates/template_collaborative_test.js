/** @odoo-module */

import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import {
    createSpreadsheetTemplate,
    displayedConnectedUsers,
    getConnectedUsersElImage,
    getSynchedStatus,
} from "../spreadsheet_test_utils";
import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import { actionService } from "@web/webclient/actions/action_service";
import { registry } from "@web/core/registry";
import {
    joinSession,
    leaveSession,
} from "@spreadsheet_edition/../tests/utils/collaborative_helpers";
import { session } from "@web/session";

/** @type {HTMLElement} */
let target;

QUnit.module(
    "documents_spreadsheet > Template Collaborative Control Panel",
    {
        beforeEach: function () {
            target = getFixture();
        },
    },
    function () {
        QUnit.test("Number of connected users is correctly rendered", async function (assert) {
            const { transportService } = await createSpreadsheetTemplate();
            assert.equal(
                displayedConnectedUsers(target),
                1,
                "It should display one connected user"
            );
            assert.hasClass(
                getConnectedUsersElImage(target),
                "fa-user",
                "It should display the fa-user icon"
            );
            joinSession(transportService, { id: 1234, userId: 9999 });
            await nextTick();
            assert.equal(
                displayedConnectedUsers(target),
                2,
                "It should display two connected users"
            );
            assert.hasClass(
                getConnectedUsersElImage(target),
                "fa-users",
                "It should display the fa-users icon"
            );

            // The same user is connected with two different tabs.
            joinSession(transportService, { id: 4321, userId: 9999 });
            await nextTick();
            assert.equal(
                displayedConnectedUsers(target),
                2,
                "It should display two connected users"
            );

            leaveSession(transportService, 4321);
            await nextTick();
            assert.equal(
                displayedConnectedUsers(target),
                2,
                "It should display two connected users"
            );

            leaveSession(transportService, 1234);
            await nextTick();
            assert.equal(
                displayedConnectedUsers(target),
                1,
                "It should display one connected user"
            );
        });

        QUnit.test("collaborative session client has the user id", async function (assert) {
            const { model } = await createSpreadsheetTemplate();
            const clients = [...model.getters.getConnectedClients()];
            assert.strictEqual(clients.length, 1);
            const localClient = clients[0];
            assert.strictEqual(localClient.name, "Mitchell");
            assert.strictEqual(localClient.userId, session.user_context.uid);
        });

        QUnit.test("Sync status is correctly rendered", async function (assert) {
            const { model, transportService } = await createSpreadsheetTemplate();
            await nextTick();
            assert.strictEqual(getSynchedStatus(target), " Saved");
            await transportService.concurrent(async () => {
                setCellContent(model, "A1", "hello");
                await nextTick();
                assert.strictEqual(getSynchedStatus(target), " Saving");
            });
            await nextTick();
            assert.strictEqual(getSynchedStatus(target), " Saved");
        });

        QUnit.test("receiving bad revision reload", async function (assert) {
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("actionMain", actionService);
            const fakeActionService = {
                dependencies: ["actionMain"],
                start(env, { actionMain }) {
                    return Object.assign({}, actionMain, {
                        doAction: (actionRequest, options = {}) => {
                            if (actionRequest === "reload_context") {
                                assert.step("reload");
                                return Promise.resolve();
                            }
                            return actionMain.doAction(actionRequest, options);
                        },
                    });
                },
            };
            serviceRegistry.add("action", fakeActionService, { force: true });
            const { transportService } = await createSpreadsheetTemplate();
            transportService.broadcast({
                type: "REMOTE_REVISION",
                serverRevisionId: "an invalid revision id",
                nextRevisionId: "the next revision id",
                revision: {},
            });
            assert.verifySteps(["reload"]);
        });
    }
);
