/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeTestEnv } from "../../helpers/mock_env";
import { makeFakeRouterService } from "../../helpers/mock_services";
import { setupWebClientRegistries, doAction, getActionManagerServerData } from "./../helpers";

let serverData;
const serviceRegistry = registry.category("services");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
    });

    QUnit.module("URL actions");

    QUnit.test("execute an 'ir.actions.act_url' action with target 'self'", async (assert) => {
        serviceRegistry.add(
            "router",
            makeFakeRouterService({
                onRedirect(url) {
                    assert.step(url);
                },
            })
        );
        setupWebClientRegistries();
        const env = await makeTestEnv({ serverData });
        await doAction(env, {
            type: "ir.actions.act_url",
            target: "self",
            url: "/my/test/url",
        });
        assert.verifySteps(["/my/test/url"]);
    });
});
