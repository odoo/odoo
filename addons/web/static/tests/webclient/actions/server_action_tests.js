/** @odoo-module **/

import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";
import { getFixture } from "../../helpers/utils";

let serverData;
let target;

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Server actions");

    QUnit.test("can execute server actions from db ID", async function (assert) {
        assert.expect(10);
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/web/action/run") {
                assert.strictEqual(args.action_id, 2, "should call the correct server action");
                return Promise.resolve(1); // execute action 1
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 2);
        assert.containsOnce(target, ".o_control_panel", "should have rendered a control panel");
        assert.containsOnce(target, ".o_kanban_view", "should have rendered a kanban view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/action/run",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    QUnit.test("handle server actions returning false", async function (assert) {
        assert.expect(10);
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/web/action/run") {
                return Promise.resolve(false);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        // execute an action in target="new"
        function onClose() {
            assert.step("close handler");
        }
        await doAction(webClient, 5, { onClose });
        assert.containsOnce(
            document.body,
            ".o_technical_modal .o_form_view",
            "should have rendered a form view in a modal"
        );
        // execute a server action that returns false
        await doAction(webClient, 2);
        assert.containsNone(document.body, ".o_technical_modal", "should have closed the modal");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "onchange",
            "/web/action/load",
            "/web/action/run",
            "close handler",
        ]);
    });

    QUnit.test("send correct context when executing a server action", async function (assert) {
        assert.expect(1);

        serverData.actions[2].context = { someKey: 44 };
        const mockRPC = async (route, args) => {
            if (route === "/web/action/run") {
                assert.deepEqual(args.context, {
                    // user context
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                    // action context
                    someKey: 44,
                });
                return Promise.resolve(1); // execute action 1
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 2);
    });

    QUnit.skipWOWL("action with html help returned by a server action", async function (assert) {
        assert.expect(1);

        serverData.actions[2].context = { someKey: 44 };
        const mockRPC = async (route, args) => {
            if (route === "/web/action/run") {
                return Promise.resolve({
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                    help: "<p>I am not a helper</p>",
                    domain: [[0, "=", 1]],
                });
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 2);

        assert.strictEqual(
            target.querySelector(".o_list_view .o_nocontent_help p").innerText,
            "I am not a helper"
        );
    });
});
