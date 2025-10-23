import { after, describe, expect, test } from "@odoo/hoot";
import { on } from "@odoo/hoot-dom";
import { mockFetch } from "@odoo/hoot-mock";

import {
    ConnectionAbortedError,
    ConnectionLostError,
    RPCError,
    rpc,
    rpcBus,
} from "@web/core/network/rpc";

const onRpcRequest = (listener) => after(on(rpcBus, "RPC:REQUEST", listener));
const onRpcResponse = (listener) => after(on(rpcBus, "RPC:RESPONSE", listener));

describe.current.tags("headless");

test("can perform a simple rpc", async () => {
    mockFetch((_, { body }) => {
        const bodyObject = JSON.parse(body);
        expect(bodyObject.jsonrpc).toBe("2.0");
        expect(bodyObject.method).toBe("call");
        expect(bodyObject.id).toBeOfType("integer");
        return { result: { action_id: 123 } };
    });

    expect(await rpc("/test/")).toEqual({ action_id: 123 });
});

test("trigger an error when response has 'error' key", async () => {
    mockFetch(() => ({
        error: {
            message: "message",
            code: 12,
            data: {
                debug: "data_debug",
                message: "data_message",
            },
        },
    }));

    const error = new RPCError("message");
    await expect(rpc("/test/")).rejects.toThrow(error);
});

test("rpc with simple routes", async () => {
    mockFetch((route, { body }) => ({
        result: { route, params: JSON.parse(body).params },
    }));

    expect(await rpc("/my/route")).toEqual({ route: "/my/route", params: {} });
    expect(await rpc("/my/route", { hey: "there", model: "test" })).toEqual({
        route: "/my/route",
        params: { hey: "there", model: "test" },
    });
});

test("check trigger RPC:REQUEST and RPC:RESPONSE for a simple rpc", async () => {
    mockFetch(() => ({ result: {} }));

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
    expect.verifySteps(["RPC:REQUEST", "RPC:RESPONSE(ok)"]);

    await rpc("/test/", {}, { silent: true });
    expect(rpcIdsRequest.toString()).toBe(rpcIdsResponse.toString());
    expect.verifySteps(["RPC:REQUEST(silent)", "RPC:RESPONSE(silent)(ok)"]);
});

test("check trigger RPC:REQUEST and RPC:RESPONSE for a rpc with an error", async () => {
    mockFetch(() => ({
        error: {
            message: "message",
            code: 12,
            data: {
                debug: "data_debug",
                message: "data_message",
            },
        },
    }));

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
    expect.verifySteps(["RPC:REQUEST", "RPC:RESPONSE(ko)"]);
});

test("check connection aborted", async () => {
    mockFetch(() => new Promise(() => {}));
    onRpcRequest(() => expect.step("RPC:REQUEST"));
    onRpcResponse(() => expect.step("RPC:RESPONSE"));

    const connection = rpc();
    connection.abort();
    const error = new ConnectionAbortedError();
    await expect(connection).rejects.toThrow(error);
    expect.verifySteps(["RPC:REQUEST", "RPC:RESPONSE"]);
});

test("trigger a ConnectionLostError when response isn't json parsable", async () => {
    mockFetch(() => new Response("<h...", { status: 500 }));

    const error = new ConnectionLostError("/test/");
    await expect(rpc("/test/")).rejects.toThrow(error);
});

test("rpc can send additional headers", async () => {
    mockFetch((url, settings) => {
        expect(settings.headers).toEqual(
            new Headers([
                ["Content-Type", "application/json"],
                ["Hello", "World"],
            ])
        );
        return { result: true };
    });
    await rpc("/test/", null, { headers: { Hello: "World" } });
});
