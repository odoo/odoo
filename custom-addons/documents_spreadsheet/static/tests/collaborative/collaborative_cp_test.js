/** @odoo-module */

import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import {
    createSpreadsheet,
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
    "documents_spreadsheet > Collaborative Control Panel",
    {
        beforeEach: function () {
            target = getFixture();
        },
    },
    function () {
        QUnit.test("Number of connected users is correctly rendered", async function (assert) {
            assert.expect(7);
            const { transportService } = await createSpreadsheet();
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
            const uid = session.user_context.uid;
            const { model } = await createSpreadsheet();
            const clients = [...model.getters.getConnectedClients()];
            assert.strictEqual(clients.length, 1);
            const localClient = clients[0];
            assert.strictEqual(localClient.name, "Mitchell");
            assert.strictEqual(localClient.userId, uid);
        });

        QUnit.test("Sync status is correctly rendered", async function (assert) {
            assert.expect(3);
            const { model, transportService } = await createSpreadsheet();
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
            assert.expect(2);
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
            const { transportService } = await createSpreadsheet();
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
