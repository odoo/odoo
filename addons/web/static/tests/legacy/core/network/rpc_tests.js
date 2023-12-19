/** @odoo-module alias=@web/../tests/core/network/rpc_tests default=false */

import { browser } from "@web/core/browser/browser";
import { ConnectionAbortedError, ConnectionLostError, rpc, rpcBus } from "@web/core/network/rpc";
import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { makeMockXHR } from "../../helpers/mock_services";
import { makeDeferred, patchWithCleanup } from "../../helpers/utils";
import { registerCleanup } from "../../helpers/cleanup";

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
    await makeTestEnv({ serviceRegistry });
    isDeployed = true;
    registerCleanup(() => (isDeployed = false));
    await rpc(route, params);
    return { url, request };
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

QUnit.module("RPC", {
    beforeEach() {
        serviceRegistry.add("notification", notificationService);
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

    await makeTestEnv({ serviceRegistry });
    const result = await rpc("/test/");
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

    await makeTestEnv({ serviceRegistry });
    try {
        await rpc("/test/");
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

QUnit.test("check trigger RPC:REQUEST and RPC:RESPONSE for a simple rpc", async (assert) => {
    const MockXHR = makeMockXHR({ test: true }, () => 1);
    patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

    await makeTestEnv({ serviceRegistry });
    const rpcIdsRequest = [];
    const rpcIdsResponse = [];
    const onRPCRequest = (ev) => {
        rpcIdsRequest.push(ev.detail.data.id);
        const silent = ev.detail.settings.silent;
        assert.step("RPC:REQUEST" + (silent ? "(silent)" : ""));
    };
    const onRPCResponse = (ev) => {
        rpcIdsResponse.push(ev.detail.data.id);
        const silent = ev.detail.settings.silent ? "(silent)" : "";
        const success = "result" in ev.detail ? "(ok)" : "";
        const fail = "error" in ev.detail ? "(ko)" : "";
        assert.step("RPC:RESPONSE" + silent + success + fail);
    };
    rpcBus.addEventListener("RPC:REQUEST", onRPCRequest);
    rpcBus.addEventListener("RPC:RESPONSE", onRPCResponse);
    registerCleanup(() => {
        rpcBus.removeEventListener("RPC:REQUEST", onRPCRequest);
        rpcBus.removeEventListener("RPC:RESPONSE", onRPCResponse);
    });
    await rpc("/test/");
    assert.strictEqual(rpcIdsRequest.toString(), rpcIdsResponse.toString());
    assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE(ok)"]);

    await rpc("/test/", {}, { silent: true });
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
    await makeTestEnv({ serviceRegistry });
    const rpcIdsRequest = [];
    const rpcIdsResponse = [];
    const onRPCRequest = (ev) => {
        rpcIdsRequest.push(ev);
        assert.step("RPC:REQUEST");
    };
    const onRPCResponse = (ev) => {
        rpcIdsResponse.push(ev);
        const silent = ev.detail.settings.silent ? "(silent)" : "";
        const success = "result" in ev.detail ? "(ok)" : "";
        const fail = "error" in ev.detail ? "(ko)" : "";
        assert.step("RPC:RESPONSE" + silent + success + fail);
    };
    rpcBus.addEventListener("RPC:REQUEST", onRPCRequest);
    rpcBus.addEventListener("RPC:RESPONSE", onRPCResponse);
    registerCleanup(() => {
        rpcBus.removeEventListener("RPC:REQUEST", onRPCRequest);
        rpcBus.removeEventListener("RPC:RESPONSE", onRPCResponse);
    });
    try {
        await rpc("/test/");
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
    await makeTestEnv({ serviceRegistry });
    const onRPCRequest = () => assert.step("RPC:REQUEST");
    const onRPCResponse = (ev) => assert.step("RPC:RESPONSE");
    rpcBus.addEventListener("RPC:REQUEST", onRPCRequest);
    rpcBus.addEventListener("RPC:RESPONSE", onRPCResponse);
    registerCleanup(() => {
        rpcBus.removeEventListener("RPC:REQUEST", onRPCRequest);
        rpcBus.removeEventListener("RPC:RESPONSE", onRPCResponse);
    });

    const connection = rpc();
    connection.abort();
    assert.rejects(connection, ConnectionAbortedError);
    assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE"]);
});

QUnit.test("trigger a ConnectionLostError when response isn't json parsable", async (assert) => {
    await makeTestEnv({ serviceRegistry });

    const MockXHR = makeMockXHR({}, () => {});
    const request = new MockXHR();
    request.response = "<h...";
    request.status = "500";

    try {
        await rpc("/test/", null, { xhr: request });
    } catch (e) {
        assert.ok(e instanceof ConnectionLostError);
    }
});
