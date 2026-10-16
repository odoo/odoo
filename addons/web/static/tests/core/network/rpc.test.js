import { after, describe, expect, test } from "@odoo/hoot";
import { on } from "@odoo/hoot-dom";
import { mockFetch } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";

import {
    ConnectionAbortedError,
    ConnectionLostError,
    RequestEntityTooLargeError,
    RPCError,
    rpc,
    rpcBus,
} from "@web/core/network/rpc";
import { RPCCache } from "@web/core/network/rpc_cache";

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
    onRpcResponse(({ detail }) => {
        expect(detail.error).toEqual(error);
    });
    await expect(rpc("/test/")).rejects.toThrow(error);
});

test("trigger a RequestEntityTooLargeError when status is 413 even if response isn't json parsable", async () => {
    mockFetch(() => new Response("<h...", { status: 413 }));
    const error = new RequestEntityTooLargeError();
    onRpcResponse(({ detail }) => {
        expect(detail.error).toEqual(error);
    });
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

test("Cache: can cache a simple rpc", async () => {
    rpc.setCache(
        new RPCCache(
            "mockRpc",
            1,
            "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
        )
    );
    mockFetch(() => {
        expect.step("Fetch");
        return { result: { action_id: 123 } };
    });

    expect(await rpc("/test/", {}, { cache: true })).toEqual({ action_id: 123 });
    expect(await rpc("/test/", {}, { cache: true })).toEqual({ action_id: 123 });
    expect(await rpc("/test/", {}, { cache: true })).toEqual({ action_id: 123 });
    expect.verifySteps(["Fetch"]);
});

const Markup = markup("").constructor;

test("markup values signaled by the server are hydrated", async () => {
    mockFetch(() => ({
        result: { a: ["<b>", "<i>"], b: { c: "<u>" }, d: "<s>" },
        markup: [["a", 1], ["b", "c"]],
    }));
    onRpcResponse(({ detail }) => {
        expect(detail.result.a[1]).toBeInstanceOf(Markup);
    });

    const result = await rpc("/test/");
    expect(result.a[0]).toBe("<b>");
    expect(result.a[1]).toBeInstanceOf(Markup);
    expect(String(result.a[1])).toBe("<i>");
    expect(result.b.c).toBeInstanceOf(Markup);
    expect(result.d).toBe("<s>");
});

test("markup result is hydrated", async () => {
    mockFetch(() => ({ result: "<b>", markup: [[]] }));

    const result = await rpc("/test/");
    expect(result).toBeInstanceOf(Markup);
    expect(String(result)).toBe("<b>");
});

test("Cache: markup values are preserved", async () => {
    rpc.setCache(
        new RPCCache(
            "mockRpc",
            1,
            "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
        )
    );
    mockFetch(() => {
        expect.step("Fetch");
        return { result: { a: "<b>", b: "<i>" }, markup: [["a"]] };
    });
    const callback = (result) => {
        expect.step("callback");
        expect(result.a).toBeInstanceOf(Markup);
        expect(result.b).toBe("<i>");
    };

    for (let i = 0; i < 2; i++) {
        const result = await rpc("/test/", {}, { cache: { callback, update: "always" } });
        expect(result.a).toBeInstanceOf(Markup);
        expect(String(result.a)).toBe("<b>");
        expect(result.b).toBe("<i>");
    }
    // the second call resolves from the cache, then calls back after fetching
    await expect.waitForSteps(["Fetch", "callback", "Fetch", "callback"]);
});
