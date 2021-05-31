/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeTestEnv } from "../../helpers/mock_env";
import { makeFakeRouterService } from "../../helpers/mock_services";
import { doAction, getActionManagerTestConfig } from "./helpers";

let testConfig;
const serviceRegistry = registry.category("services");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        testConfig = getActionManagerTestConfig();
    });

    QUnit.module("URL actions");

    QUnit.test("execute an 'ir.actions.act_url' action with target 'self'", async (assert) => {
        serviceRegistry.add(
            "router",
            makeFakeRouterService({
                redirect: (url) => {
                    assert.step(url);
                },
            }),
            { force: true }
        );
        const env = await makeTestEnv(testConfig);
        await doAction(env, {
            type: "ir.actions.act_url",
            target: "self",
            url: "/my/test/url",
        });
        assert.verifySteps(["/my/test/url"]);
    });
});
