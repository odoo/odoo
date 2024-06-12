/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ConnectionAbortedError, ConnectionLostError, rpcService } from "@web/core/network/rpc_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { makeMockXHR } from "../../helpers/mock_services";
import {
    destroy,
    getFixture,
    makeDeferred,
    mount,
    nextTick,
    patchWithCleanup,
} from "../../helpers/utils";
import { registerCleanup } from "../../helpers/cleanup";

import { Component, xml } from "@odoo/owl";

const serviceRegistry = registry.category("services");

let isDeployed = false;
async function testRPC(route, params) {
    let url = "";
    let request;
    const MockXHR = makeMockXHR({ test: true }, function (data) {
        request = data;
        url = this.url;
    });
    patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

    if (isDeployed) {
        clearRegistryWithCleanup(registry.category("main_components"));
    }
    const env = await makeTestEnv({
        serviceRegistry,
        // browser: { XMLHttpRequest: MockXHR },
    });
    isDeployed = true;
    registerCleanup(() => (isDeployed = false));
    await env.services.rpc(route, params);
    return { url, request };
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

QUnit.module("RPC", {
    beforeEach() {
        serviceRegistry.add("notification", notificationService);
        serviceRegistry.add("rpc", rpcService);
    },
});

QUnit.test("can perform a simple rpc", async (assert) => {
    assert.expect(4);
    const MockXHR = makeMockXHR({ result: { action_id: 123 } }, (request) => {
        assert.strictEqual(request.jsonrpc, "2.0");
        assert.strictEqual(request.method, "call");
        assert.ok(typeof request.id === "number");
    });

    patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

    const env = await makeTestEnv({ serviceRegistry });
    const result = await env.services.rpc("/test/");
    assert.deepEqual(result, { action_id: 123 });
});

QUnit.test("trigger an error when response has 'error' key", async (assert) => {
    assert.expect(1);
    const error = {
        message: "message",
        code: 12,
        data: {
            debug: "data_debug",
            message: "data_message",
        },
    };
    const MockXHR = makeMockXHR({ error });
    patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

    const env = await makeTestEnv({
        serviceRegistry,
    });
    try {
        await env.services.rpc("/test/");
    } catch {
        assert.ok(true);
    }
});

QUnit.test("rpc with simple routes", async (assert) => {
    const info1 = await testRPC("/my/route");
    assert.strictEqual(info1.url, "/my/route");
    const info2 = await testRPC("/my/route", { hey: "there", model: "test" });
    assert.deepEqual(info2.request.params, {
        hey: "there",
        model: "test",
    });
});

QUnit.test("rpc coming from destroyed components are left pending", async (assert) => {
    class MyComponent extends Component {
        setup() {
            this.rpc = useService("rpc");
        }
    }
    MyComponent.template = xml`<div/>`;
    const def = makeDeferred();
    const MockXHR = makeMockXHR({ result: "1" }, () => {}, def);
    patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

    const env = await makeTestEnv({
        serviceRegistry,
    });
    const target = getFixture();
    const component = await mount(MyComponent, target, { env });
    let isResolved = false;
    let isFailed = false;
    component
        .rpc("/my/route")
        .then(() => {
            isResolved = true;
        })
        .catch(() => {
            isFailed = true;
        });
    assert.strictEqual(isResolved, false);
    assert.strictEqual(isFailed, false);
    destroy(component);
    def.resolve();
    await nextTick();
    assert.strictEqual(isResolved, false);
    assert.strictEqual(isFailed, false);
});

QUnit.test("rpc initiated from destroyed components throw exception", async (assert) => {
    assert.expect(1);
    class MyComponent extends Component {
        setup() {
            this.rpc = useService("rpc");
        }
    }
    MyComponent.template = xml`<div/>`;
    const env = await makeTestEnv({
        serviceRegistry,
    });
    const target = getFixture();
    const component = await mount(MyComponent, target, { env });
    destroy(component);
    try {
        await component.rpc("/my/route");
    } catch (e) {
        assert.strictEqual(e.message, "Component is destroyed");
    }
});

QUnit.test("check trigger RPC:REQUEST and RPC:RESPONSE for a simple rpc", async (assert) => {
    const MockXHR = makeMockXHR({ test: true }, () => 1);
    patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

    const env = await makeTestEnv({
        serviceRegistry,
    });
    const rpcIdsRequest = [];
    const rpcIdsResponse = [];
    env.bus.addEventListener("RPC:REQUEST", (ev) => {
        rpcIdsRequest.push(ev.detail.data.id);
        const silent = ev.detail.settings.silent;
        assert.step("RPC:REQUEST" + (silent ? "(silent)" : ""));
    });
    env.bus.addEventListener("RPC:RESPONSE", (ev) => {
        rpcIdsResponse.push(ev.detail.data.id);
        const silent = ev.detail.settings.silent ? "(silent)" : "";
        const success = "result" in ev.detail ? "(ok)" : "";
        const fail = "error" in ev.detail ? "(ko)" : "";
        assert.step("RPC:RESPONSE" + silent + success + fail);
    });
    await env.services.rpc("/test/");
    assert.strictEqual(rpcIdsRequest.toString(), rpcIdsResponse.toString());
    assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE(ok)"]);

    await env.services.rpc("/test/", {}, { silent: true });
    assert.verifySteps(["RPC:REQUEST(silent)", "RPC:RESPONSE(silent)(ok)"]);
});

QUnit.test("check trigger RPC:REQUEST and RPC:RESPONSE for a rpc with an error", async (assert) => {
    const error = {
        message: "message",
        code: 12,
        data: {
            debug: "data_debug",
            message: "data_message",
        },
    };
    const MockXHR = makeMockXHR({ error });
    patchWithCleanup(browser, { XMLHttpRequest: MockXHR });
    const env = await makeTestEnv({
        serviceRegistry,
    });
    const rpcIdsRequest = [];
    const rpcIdsResponse = [];
    env.bus.addEventListener("RPC:REQUEST", (ev) => {
        rpcIdsRequest.push(ev);
        assert.step("RPC:REQUEST");
    });
    env.bus.addEventListener("RPC:RESPONSE", (ev) => {
        rpcIdsResponse.push(ev);
        const silent = ev.detail.settings.silent ? "(silent)" : "";
        const success = "result" in ev.detail ? "(ok)" : "";
        const fail = "error" in ev.detail ? "(ko)" : "";
        assert.step("RPC:RESPONSE" + silent + success + fail);
    });
    try {
        await env.services.rpc("/test/");
    } catch {
        assert.step("ok");
    }
    assert.strictEqual(rpcIdsRequest.toString(), rpcIdsResponse.toString());
    assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE(ko)", "ok"]);
});

QUnit.test("check connection aborted", async (assert) => {
    const def = makeDeferred();
    const MockXHR = makeMockXHR({}, () => {}, def);
    patchWithCleanup(browser, { XMLHttpRequest: MockXHR });
    const env = await makeTestEnv({ serviceRegistry });
    env.bus.addEventListener("RPC:REQUEST", () => {
        assert.step("RPC:REQUEST");
    });
    env.bus.addEventListener("RPC:RESPONSE", () => {
        assert.step("RPC:RESPONSE");
    });

    const connection = env.services.rpc();
    connection.abort();
    assert.rejects(connection, ConnectionAbortedError);
    assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE"]);
});

QUnit.test("trigger a ConnectionLostError when response isn't json parsable", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });

    const MockXHR = makeMockXHR({}, () => {});
    const request = new MockXHR();
    request.response = "<h...";
    request.status = "500";

    try {
        await env.services.rpc("/test/", null, { xhr: request });
    } catch (e) {
        assert.ok(e instanceof ConnectionLostError);
    }
});
