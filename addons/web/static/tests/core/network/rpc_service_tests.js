/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ConnectionAbortedError, rpcService } from "@web/core/network/rpc_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch, unpatch } from "@web/core/utils/patch";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { makeMockXHR } from "../../helpers/mock_services";
import { getFixture, makeDeferred, nextTick, patchWithCleanup } from "../../helpers/utils";
import { registerCleanup } from "../../helpers/cleanup";

const { Component, mount, tags } = owl;
const { xml } = tags;

let isXHRMocked = false;
const serviceRegistry = registry.category("services");

let isDeployed = false;
async function testRPC(route, params) {
    let url = "";
    let request;
    let MockXHR = makeMockXHR({ test: true }, function (data) {
        request = data;
        url = this.url;
    });
    if (isXHRMocked) {
        unpatch(browser, "mock.xhr");
    }
    patch(
        browser,
        "mock.xhr",
        {
            XMLHttpRequest: MockXHR,
        },
        { pure: true }
    );
    isXHRMocked = true;

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
    afterEach() {
        if (isXHRMocked) {
            unpatch(browser, "mock.xhr");
            isXHRMocked = false;
        }
    },
});

QUnit.test("can perform a simple rpc", async (assert) => {
    assert.expect(4);
    let MockXHR = makeMockXHR({ result: { action_id: 123 } }, (request) => {
        assert.strictEqual(request.jsonrpc, "2.0");
        assert.strictEqual(request.method, "call");
        assert.ok(typeof request.id === "number");
    });

    patch(browser, "mock.xhr", { XMLHttpRequest: MockXHR }, { pure: true });

    const env = await makeTestEnv({ serviceRegistry });
    const result = await env.services.rpc("/test/");
    assert.deepEqual(result, { action_id: 123 });
    unpatch(browser, "mock.xhr");
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
    let MockXHR = makeMockXHR({ error });
    patch(browser, "mock.xhr", { XMLHttpRequest: MockXHR }, { pure: true });

    const env = await makeTestEnv({
        serviceRegistry,
    });
    try {
        await env.services.rpc("/test/");
    } catch (error) {
        assert.ok(true);
    }
    unpatch(browser, "mock.xhr");
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
    let MockXHR = makeMockXHR({ result: "1" }, () => {}, def);
    patch(browser, "mock.xhr", { XMLHttpRequest: MockXHR }, { pure: true });

    const env = await makeTestEnv({
        serviceRegistry,
    });
    const target = getFixture();
    const component = await mount(MyComponent, { env, target });
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
    component.destroy();
    def.resolve();
    await nextTick();
    assert.strictEqual(isResolved, false);
    assert.strictEqual(isFailed, false);
    unpatch(browser, "mock.xhr");
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
    const component = await mount(MyComponent, { env, target });
    component.destroy();
    try {
        await component.rpc("/my/route");
    } catch (e) {
        assert.strictEqual(e.message, "Component is destroyed");
    }
});

QUnit.test("check trigger RPC:REQUEST and RPC:RESPONSE for a simple rpc", async (assert) => {
    let MockXHR = makeMockXHR({ test: true }, () => 1);
    patch(browser, "mock.xhr", { XMLHttpRequest: MockXHR }, { pure: true });

    const env = await makeTestEnv({
        serviceRegistry,
    });
    let rpcIdsRequest = [];
    let rpcIdsResponse = [];
    env.bus.on("RPC:REQUEST", null, (rpcId) => {
        rpcIdsRequest.push(rpcId);
        assert.step("RPC:REQUEST");
    });
    env.bus.on("RPC:RESPONSE", null, (rpcId) => {
        rpcIdsResponse.push(rpcId);
        assert.step("RPC:RESPONSE");
    });
    await env.services.rpc("/test/");
    assert.strictEqual(rpcIdsRequest.toString(), rpcIdsResponse.toString());
    assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE"]);

    await env.services.rpc("/test/", {}, { silent: true });
    assert.verifySteps([]);

    unpatch(browser, "mock.xhr");
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
    let MockXHR = makeMockXHR({ error });
    patch(browser, "mock.xhr", { XMLHttpRequest: MockXHR }, { pure: true });
    const env = await makeTestEnv({
        serviceRegistry,
    });
    let rpcIdsRequest = [];
    let rpcIdsResponse = [];
    env.bus.on("RPC:REQUEST", null, (rpcId) => {
        rpcIdsRequest.push(rpcId);
        assert.step("RPC:REQUEST");
    });
    env.bus.on("RPC:RESPONSE", null, (rpcId) => {
        rpcIdsResponse.push(rpcId);
        assert.step("RPC:RESPONSE");
    });
    try {
        await env.services.rpc("/test/");
    } catch (e) {
        assert.ok(true);
    }
    assert.strictEqual(rpcIdsRequest.toString(), rpcIdsResponse.toString());
    assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE"]);
    unpatch(browser, "mock.xhr");
});

QUnit.test("check connection aborted", async (assert) => {
    const def = makeDeferred();
    let MockXHR = makeMockXHR({}, () => {}, def);
    patchWithCleanup(browser, { XMLHttpRequest: MockXHR }, { pure: true });
    const env = await makeTestEnv({ serviceRegistry });
    env.bus.on("RPC:REQUEST", null, (rpcId) => {
        assert.step("RPC:REQUEST");
    });
    env.bus.on("RPC:RESPONSE", null, (rpcId) => {
        assert.step("RPC:RESPONSE");
    });

    const connection = env.services.rpc();
    connection.abort();
    assert.rejects(connection, ConnectionAbortedError);
    assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE"]);
});

QUnit.test(
    "Response with status 404 and invalid JSON response result in a rerror with a readable message",
    async (assert) => {
        const env = await makeTestEnv({ serviceRegistry });

        const MockXHR = makeMockXHR({}, () => {});
        const request = new MockXHR();
        request.response = "<h...";
        request.status = "404";

        try {
            await env.services.rpc("/test/", null, { xhr: request });
        } catch (_e) {
            assert.strictEqual(
                _e.message,
                "server responded with invalid JSON response (HTTP404): <h..."
            );
        }
    }
);
