/** @odoo-module alias=@web/../tests/webclient/actions/server_action_tests default=false */

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
        assert.expect(8);
        serverData.actions[2].code = () => {
            return {
                xml_id: "action_1",
                name: "Partners Action 1",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[1, "kanban"]],
            };
        };
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/web/action/load") {
                assert.strictEqual(args.action_id, 2, "should call the correct server action");
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 2);
        assert.containsOnce(target, ".o_control_panel", "should have rendered a control panel");
        assert.containsOnce(target, ".o_kanban_view", "should have rendered a kanban view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    QUnit.test(
        "send correct context when load it could execute a server action",
        async function (assert) {
            assert.expect(1);

            const mockRPC = async (route, args) => {
                if (route === "/web/action/load") {
                    assert.deepEqual(args.context, {
                        // user context
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                        // action context
                        someKey: 44,
                    });
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 2, { additionalContext: { someKey: 44 } });
        }
    );

    QUnit.test("action with html help returned by a server action", async function (assert) {
        serverData.actions[2].code = () => {
            return {
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
                help: "<p>I am not a helper</p>",
                domain: [[0, "=", 1]],
            };
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 2);

        assert.strictEqual(
            target.querySelector(".o_list_view .o_nocontent_help p").innerText,
            "I am not a helper"
        );
    });
});
