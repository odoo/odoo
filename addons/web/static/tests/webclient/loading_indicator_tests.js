/** @odoo-module **/

import { browser as originalBrowser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { patch, unpatch } from "@web/core/utils/patch";
import { LoadingIndicator } from "@web/webclient/loading_indicator/loading_indicator";
import { makeTestEnv } from "../helpers/mock_env";
import {
    getFixture,
    mockTimeout,
    mount,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";

const serviceRegistry = registry.category("services");

let target;

QUnit.module("LoadingIndicator", {
    async beforeEach() {
        target = getFixture();
        serviceRegistry.add("ui", uiService);
        patchWithCleanup(originalBrowser, {
            setTimeout: async (f) => {
                await Promise.resolve();
                f();
            },
        });
    },
});

QUnit.test("displays the loading indicator in non debug mode", async (assert) => {
    const env = await makeTestEnv();
    await mount(LoadingIndicator, target, { env });
    let loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
    env.bus.trigger("RPC:REQUEST", 1);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.notStrictEqual(loadingIndicator, null, "the loading indicator should be displayed");
    assert.strictEqual(
        loadingIndicator.textContent,
        "Loading",
        "the loading indicator should display 'Loading'"
    );
    env.bus.trigger("RPC:RESPONSE", 1);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
});

QUnit.test("displays the loading indicator for one rpc in debug mode", async (assert) => {
    patchWithCleanup(odoo, { debug: "1" });
    const env = await makeTestEnv();
    await mount(LoadingIndicator, target, { env });
    let loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
    env.bus.trigger("RPC:REQUEST", 1);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.notStrictEqual(loadingIndicator, null, "the loading indicator should be displayed");
    assert.strictEqual(
        loadingIndicator.textContent,
        "Loading (1)",
        "the loading indicator should indicate 1 request in progress"
    );
    env.bus.trigger("RPC:RESPONSE", 1);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
});

QUnit.test("displays the loading indicator for multi rpc in debug mode", async (assert) => {
    patchWithCleanup(odoo, { debug: "1" });
    const env = await makeTestEnv();
    await mount(LoadingIndicator, target, { env });
    let loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
    env.bus.trigger("RPC:REQUEST", 1);
    env.bus.trigger("RPC:REQUEST", 2);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.notStrictEqual(loadingIndicator, null, "the loading indicator should be displayed");
    assert.strictEqual(
        loadingIndicator.textContent,
        "Loading (2)",
        "the loading indicator should indicate 2 requests in progress."
    );
    env.bus.trigger("RPC:REQUEST", 3);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(
        loadingIndicator.textContent,
        "Loading (3)",
        "the loading indicator should indicate 3 requests in progress."
    );
    env.bus.trigger("RPC:RESPONSE", 1);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(
        loadingIndicator.textContent,
        "Loading (2)",
        "the loading indicator should indicate 2 requests in progress."
    );
    env.bus.trigger("RPC:REQUEST", 4);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(
        loadingIndicator.textContent,
        "Loading (3)",
        "the loading indicator should indicate 3 requests in progress."
    );
    env.bus.trigger("RPC:RESPONSE", 2);
    env.bus.trigger("RPC:RESPONSE", 3);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(
        loadingIndicator.textContent,
        "Loading (1)",
        "the loading indicator should indicate 1 request in progress."
    );
    env.bus.trigger("RPC:RESPONSE", 4);
    await nextTick();
    loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
});

QUnit.test("loading indicator blocks UI", async (assert) => {
    const env = await makeTestEnv();
    patch(originalBrowser, "mock.settimeout", {
        setTimeout: async (callback, delay) => {
            assert.step(`set timeout ${delay}`);
            await Promise.resolve();
            callback();
        },
    });
    const ui = env.services.ui;
    ui.bus.addEventListener("BLOCK", () => {
        assert.step("block");
    });
    ui.bus.addEventListener("UNBLOCK", () => {
        assert.step("unblock");
    });
    await mount(LoadingIndicator, target, { env });
    env.bus.trigger("RPC:REQUEST", 1);
    await nextTick();
    env.bus.trigger("RPC:RESPONSE", 1);
    await nextTick();
    assert.verifySteps(["set timeout 250", "set timeout 3000", "block", "unblock"]);
    unpatch(originalBrowser, "mock.settimeout");
});

QUnit.test("loading indicator doesn't unblock ui if it didn't block it", async (assert) => {
    const env = await makeTestEnv();
    const { execRegisteredTimeouts } = mockTimeout();
    const ui = env.services.ui;
    ui.bus.on("BLOCK", null, () => {
        assert.step("block");
    });
    ui.bus.on("UNBLOCK", null, () => {
        assert.step("unblock");
    });
    await mount(LoadingIndicator, target, { env });
    env.bus.trigger("RPC:REQUEST", 1);
    execRegisteredTimeouts();
    env.bus.trigger("RPC:RESPONSE", 1);
    assert.verifySteps(["block", "unblock"]);
    env.bus.trigger("RPC:REQUEST", 2);
    env.bus.trigger("RPC:RESPONSE", 2);
    execRegisteredTimeouts();
    assert.verifySteps([]);
});

QUnit.test("loading indicator is not displayed immediately", async (assert) => {
    const env = await makeTestEnv();
    const { advanceTime } = mockTimeout();

    const ui = env.services.ui;
    ui.bus.addEventListener("BLOCK", () => {
        assert.step("block");
    });
    ui.bus.addEventListener("UNBLOCK", () => {
        assert.step("unblock");
    });
    await mount(LoadingIndicator, target, { env });
    env.bus.trigger("RPC:REQUEST", 1);
    await nextTick();
    assert.containsNone(target, ".o_loading_indicator");
    await advanceTime(400);
    await nextTick();
    assert.containsOnce(target, ".o_loading_indicator");

    env.bus.trigger("RPC:RESPONSE", 1);
    await nextTick();
    assert.containsNone(target, ".o_loading_indicator");
});
