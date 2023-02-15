/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeTestEnv } from "../../helpers/mock_env";
import { makeFakeRouterService } from "../../helpers/mock_services";
import { setupWebClientRegistries, doAction, getActionManagerServerData } from "./../helpers";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";

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

    QUnit.test("an 'ir.actions.act_url' with target 'self' blocks the ui", async (assert) => {
        serviceRegistry.add(
            "ui",
            {
                start() {
                    return {
                        block: () => assert.step("block"),
                        // we can't simulate a page unload in the tests, so in this scenario the
                        // ui will be unblocked directly (and we thus need to define the unblock
                        // function)
                        unblock: () => {},
                    };
                },
            }
        );
        setupWebClientRegistries();
        const env = await makeTestEnv({ serverData });
        await doAction(env, {
            type: "ir.actions.act_url",
            target: "self",
            url: "/my/test/url",
        });
        assert.verifySteps(["block"]);
    });

    QUnit.test("execute an 'ir.actions.act_url' action with onClose option", async (assert) => {
        setupWebClientRegistries();
        patchWithCleanup(browser, {
            open: () => assert.step("browser open"),
        });
        const env = await makeTestEnv({ serverData });
        const options = {
            onClose: () => assert.step("onClose"),
        };
        await doAction(env, { type: "ir.actions.act_url" }, options);
        assert.verifySteps(["browser open", "onClose"]);
    });
});
