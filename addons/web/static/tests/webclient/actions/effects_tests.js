/** @odoo-module **/

import { registry } from "@web/core/registry";
import testUtils from "web.test_utils";
import { clearRegistryWithCleanup } from "../../helpers/mock_env";
import { click, legacyExtraNextTick, nextTick, patchWithCleanup } from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";
import { session } from "@web/session";

let serverData;

const mainComponentRegistry = registry.category("main_components");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
    });

    QUnit.module("Effects");

    QUnit.test("rainbowman integrated to webClient", async function (assert) {
        assert.expect(10);
        patchWithCleanup(session, { show_effect: true });
        clearRegistryWithCleanup(mainComponentRegistry);

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        assert.containsOnce(webClient.el, ".o_kanban_view");
        assert.containsNone(webClient.el, ".o_reward");
        webClient.env.services.effect.add({ type: "rainbow_man", message: "", fadeout: "no" });
        await nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(webClient.el, ".o_reward");
        assert.containsOnce(webClient.el, ".o_kanban_view");
        await testUtils.dom.click(webClient.el.querySelector(".o_kanban_record"));
        await legacyExtraNextTick();
        assert.containsNone(webClient.el, ".o_reward");
        assert.containsOnce(webClient.el, ".o_kanban_view");
        webClient.env.services.effect.add({ type: "rainbow_man", message: "", fadeout: "no" });
        await nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(webClient.el, ".o_reward");
        assert.containsOnce(webClient.el, ".o_kanban_view");
        // Do not force rainbow man to destroy on doAction
        // we let it die either after its animation or on user click
        await doAction(webClient, 3);
        assert.containsOnce(webClient.el, ".o_reward");
        assert.containsOnce(webClient.el, ".o_list_view");
    });

    QUnit.test("on close with effect from server", async function (assert) {
        assert.expect(1);
        patchWithCleanup(session, { show_effect: true });
        const mockRPC = async (route) => {
            if (route === "/web/dataset/call_button") {
                return Promise.resolve({
                    type: "ir.actions.act_window_close",
                    effect: {
                        type: "rainbow_man",
                        message: "button called",
                    },
                });
            }
        };
        clearRegistryWithCleanup(mainComponentRegistry);

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 6);
        await click(webClient.el.querySelector('button[name="object"]'));
        assert.containsOnce(webClient, ".o_reward");
    });

    QUnit.test("on close with effect in xml", async function (assert) {
        assert.expect(2);
        serverData.views["partner,false,form"] = `
            <form>
              <header>
                <button string="Call method" name="object" type="object"
                 effect="{'type': 'rainbow_man', 'message': 'rainBowInXML'}"
                />
              </header>
              <field name="display_name"/>
            </form>`;
        patchWithCleanup(session, { show_effect: true });
        const mockRPC = async (route) => {
            if (route === "/web/dataset/call_button") {
                return Promise.resolve(false);
            }
        };
        clearRegistryWithCleanup(mainComponentRegistry);

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 6);
        await click(webClient.el.querySelector('button[name="object"]'));
        await legacyExtraNextTick();
        assert.containsOnce(webClient.el, ".o_reward");
        assert.strictEqual(
            webClient.el.querySelector(".o_reward .o_reward_msg_content").textContent,
            "rainBowInXML"
        );
    });
});
