import { after, describe, expect, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";

import {
    ConnectionAbortedError,
    ConnectionLostError,
    RPCError,
    rpc,
    rpcBus,
} from "@web/core/network/rpc";

function addRpcListener(eventName, listener) {
    rpcBus.addEventListener(eventName, listener);
    after(() => rpcBus.removeEventListener(eventName, listener));
}

const onRpcRequest = (listener) => addRpcListener("RPC:REQUEST", listener);
const onRpcResponse = (listener) => addRpcListener("RPC:RESPONSE", listener);

describe.current.tags("headless");

test("can perform a simple rpc", async () => {
    const restoreFetch = mockFetch((_, { body }) => {
        const bodyObject = JSON.parse(body);
        expect(bodyObject.jsonrpc).toBe("2.0");
        expect(bodyObject.method).toBe("call");
        expect(bodyObject.id).toBeOfType("integer");
        return { result: { action_id: 123 } };
    });
    after(restoreFetch);

    expect(await rpc("/test/")).toEqual({ action_id: 123 });
});

test("trigger an error when response has 'error' key", async () => {
    const restoreFetch = mockFetch(() => ({
        error: {
            message: "message",
            code: 12,
            data: {
                debug: "data_debug",
                message: "data_message",
            },
        },
    }));
    after(restoreFetch);

    const error = new RPCError("message");
    await expect(rpc("/test/")).rejects.toThrow(error);
});

test("rpc with simple routes", async () => {
    const restoreFetch = mockFetch((route, { body }) => ({
        result: { route, params: JSON.parse(body).params },
    }));
    after(restoreFetch);

    expect(await rpc("/my/route")).toEqual({ route: "/my/route", params: {} });
    expect(await rpc("/my/route", { hey: "there", model: "test" })).toEqual({
        route: "/my/route",
        params: { hey: "there", model: "test" },
    });
});

test("check trigger RPC:REQUEST and RPC:RESPONSE for a simple rpc", async () => {
    const restoreFetch = mockFetch(() => ({ result: {} }));
    after(restoreFetch);

    const rpcIdsRequest = [];
    const rpcIdsResponse = [];

    onRpcRequest(({ detail }) => {
        rpcIdsRequest.push(detail.data.id);
        const silent = detail.settings.silent ? "(silent)" : "";
        expect.step(`RPC:REQUEST${silent}`);
    });
    onRpcResponse(({ detail }) => {
        rpcIdsResponse.push(detail.data.id);
        const silent = detail.settings.silent ? "(silent)" : "";
        const success = "result" in detail ? "(ok)" : "";
        const fail = "error" in detail ? "(ko)" : "";
        expect.step(`RPC:RESPONSE${silent}${success}${fail}`);
    });

    await rpc("/test/");
    expect(rpcIdsRequest.toString()).toBe(rpcIdsResponse.toString());
    expect(["RPC:REQUEST", "RPC:RESPONSE(ok)"]).toVerifySteps();

    await rpc("/test/", {}, { silent: true });
    expect(rpcIdsRequest.toString()).toBe(rpcIdsResponse.toString());
    expect(["RPC:REQUEST(silent)", "RPC:RESPONSE(silent)(ok)"]).toVerifySteps();
});

test("check trigger RPC:REQUEST and RPC:RESPONSE for a rpc with an error", async () => {
    const restoreFetch = mockFetch(() => ({
        error: {
            message: "message",
            code: 12,
            data: {
                debug: "data_debug",
                message: "data_message",
            },
        },
    }));
    after(restoreFetch);

    const rpcIdsRequest = [];
    const rpcIdsResponse = [];

    onRpcRequest(({ detail }) => {
        rpcIdsRequest.push(detail.data.id);
        const silent = detail.settings.silent ? "(silent)" : "";
        expect.step(`RPC:REQUEST${silent}`);
    });
    onRpcResponse(({ detail }) => {
        rpcIdsResponse.push(detail.data.id);
        const silent = detail.settings.silent ? "(silent)" : "";
        const success = "result" in detail ? "(ok)" : "";
        const fail = "error" in detail ? "(ko)" : "";
        expect.step(`RPC:RESPONSE${silent}${success}${fail}`);
    });

    const error = new RPCError("message");
    await expect(rpc("/test/")).rejects.toThrow(error);
    expect(["RPC:REQUEST", "RPC:RESPONSE(ko)"]).toVerifySteps();
});

test("check connection aborted", async () => {
    after(mockFetch(() => new Promise(() => {})));
    onRpcRequest(() => expect.step("RPC:REQUEST"));
    onRpcResponse(() => expect.step("RPC:RESPONSE"));

    const connection = rpc();
    connection.abort();
    const error = new ConnectionAbortedError();
    await expect(connection).rejects.toThrow(error);
    expect(["RPC:REQUEST", "RPC:RESPONSE"]).toVerifySteps();
});

test("trigger a ConnectionLostError when response isn't json parsable", async () => {
    const restoreFetch = mockFetch(() => new Response("<h...", { status: 500 }));
    after(restoreFetch);

    const error = new ConnectionLostError("/test/");
    await expect(rpc("/test/")).rejects.toThrow(error);
});
