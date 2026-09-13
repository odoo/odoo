// @ts-check

import {
    after,
    Deferred,
    describe,
    expect,
    runAllTimers,
    test,
    tick,
} from "@odoo/hoot";
import { on } from "@odoo/hoot-dom";
import { mockFetch } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import {
    ConnectionAbortedError,
    ConnectionLostError,
    ConnectionTimeoutError,
    InvalidResponseError,
    rpc,
    rpcBus,
    RPCError,
    ServerOverloadError,
} from "@web/core/network/rpc";
import { RPCCache } from "@web/core/network/rpc_cache";

const onRpcRequest = (listener) => after(on(rpcBus, "RPC:REQUEST", listener));
const onRpcResponse = (listener) => after(on(rpcBus, "RPC:RESPONSE", listener));

describe.current.tags("headless");

for (const settings of [{ dedup: true }, { cache: true }]) {
    test(`${settings.dedup ? "dedup" : "cache"} keeps empty and sparse request arrays distinct`, async () => {
        rpc.setCache(new RPCCache("wireIdentity", 1));
        mockFetch((_, { body }) => {
            const { params } = JSON.parse(String(body));
            expect.step(`fetch ${params.ids.length}`);
            return { result: params.ids.length };
        });
        const results = await Promise.all([
            rpc("/array-length", { ids: [] }, settings),
            rpc("/array-length", { ids: Array(1) }, settings),
        ]);
        expect(results).toEqual([0, 1]);
        expect.verifySteps(["fetch 0", "fetch 1"]);
    });
}

test("can perform a simple rpc", async () => {
    mockFetch((_, { body }) => {
        const bodyObject = JSON.parse(String(body));
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
    await expect(rpc("/test/")).rejects.toThrow(/** @type {any} */ (error));
});

test("rpc with simple routes", async () => {
    mockFetch((route, { body }) => ({
        result: { route, params: JSON.parse(String(body)).params },
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
    await expect(rpc("/test/")).rejects.toThrow(/** @type {any} */ (error));
    expect.verifySteps(["RPC:REQUEST", "RPC:RESPONSE(ko)"]);
});

test("check connection aborted", async () => {
    mockFetch(() => new Promise(() => {}));
    onRpcRequest(() => expect.step("RPC:REQUEST"));
    onRpcResponse(() => expect.step("RPC:RESPONSE"));

    const connection = rpc("/test/");
    connection.abort();
    const error = new ConnectionAbortedError();
    await expect(connection).rejects.toThrow(/** @type {any} */ (error));
    expect.verifySteps(["RPC:REQUEST", "RPC:RESPONSE"]);
});

test("abort during body streaming stays silent, no InvalidResponseError", async () => {
    /** @type {(reason?: any) => void} */
    let rejectJson;
    const response = new Response("{}", {
        status: 200,
        headers: { "Content-Type": "application/json" },
    });
    response.json = () => new Promise((_resolve, reject) => (rejectJson = reject));
    mockFetch(() => response);
    onRpcResponse(() => expect.step("RPC:RESPONSE"));

    const connection = rpc("/test/");
    connection.then(
        () => expect.step("resolved"),
        () => expect.step("rejected"),
    );
    await tick();
    await tick();
    connection.abort(false);
    rejectJson(new DOMException("The user aborted a request.", "AbortError"));
    await tick();
    await tick();

    expect.verifySteps(["RPC:RESPONSE"]);
});

test("a non-2xx JSON response rejects instead of resolving undefined", async () => {
    mockFetch(
        () =>
            new Response('{"detail": "rate limited"}', {
                status: 429,
                headers: { "Content-Type": "application/json" },
            }),
    );
    const error = await rpc("/test/").catch((e) => e);
    expect(error).toBeInstanceOf(InvalidResponseError);
});

test("a 500 JSON response is a retryable ServerOverloadError", async () => {
    mockFetch(
        () =>
            new Response('{"msg": "boom"}', {
                status: 500,
                headers: { "Content-Type": "application/json" },
            }),
    );
    const error = await rpc("/test/").catch((e) => e);
    expect(error).toBeInstanceOf(ServerOverloadError);
});

/** @param {typeof browser.fetch} fetchFn */
function patchBrowserFetch(fetchFn) {
    const originalFetch = browser.fetch;
    browser.fetch = fetchFn;
    after(() => (browser.fetch = originalFetch));
}

/** @param {AbortSignal} signal */
function streamingBodyResponse(signal) {
    const response = new Response("{}", {
        status: 200,
        headers: { "Content-Type": "application/json" },
    });
    response.json = () =>
        new Promise((_resolve, reject) => {
            signal.addEventListener("abort", () => reject(signal.reason));
        });
    return response;
}

test("settings.timeout: timeout before the response arrives is a ConnectionTimeoutError", async () => {
    patchBrowserFetch(
        (_url, { signal }) =>
            new Promise((_resolve, reject) => {
                signal?.addEventListener("abort", () => reject(signal.reason));
            }),
    );

    const error = await rpc("/test/", {}, { timeout: 10 }).catch((e) => e);
    expect(error).toBeInstanceOf(ConnectionTimeoutError);
    expect(error.timeoutMs).toBe(10);
    expect(error.url).toBe("/test/");
});

test("settings.timeout firing during the body read is a ConnectionTimeoutError, not InvalidResponseError", async () => {
    patchBrowserFetch((_url, { signal }) =>
        Promise.resolve(streamingBodyResponse(signal)),
    );

    const error = await rpc("/test/", {}, { timeout: 10 }).catch((e) => e);
    expect(error).toBeInstanceOf(ConnectionTimeoutError);
    expect(error).not.toBeInstanceOf(InvalidResponseError);
    expect(error.timeoutMs).toBe(10);
    expect(error.url).toBe("/test/");
});

test("settings.timeout: silent caller abort during body read still wins over a fired timeout", async () => {
    /** @type {(reason?: any) => void} */
    let rejectJson;
    const response = new Response("{}", {
        status: 200,
        headers: { "Content-Type": "application/json" },
    });
    response.json = () => new Promise((_resolve, reject) => (rejectJson = reject));
    mockFetch(() => response);
    onRpcResponse(() => expect.step("RPC:RESPONSE"));

    const connection = rpc("/test/", {}, { timeout: 10 });
    connection.then(
        () => expect.step("resolved"),
        () => expect.step("rejected"),
    );
    await tick();
    await new Promise((resolve) => setTimeout(resolve, 30));
    connection.abort(false);
    rejectJson(new DOMException("The operation timed out.", "TimeoutError"));
    await tick();
    await tick();

    expect.verifySteps(["RPC:RESPONSE"]);
});

test("Retry: mid-body timeout is retryable", async () => {
    let fetchCount = 0;
    patchBrowserFetch((_url, { signal }) => {
        fetchCount++;
        return Promise.resolve(streamingBodyResponse(signal));
    });

    const prom = rpc(
        "/test/",
        {},
        { timeout: 10, retry: { retries: 1, baseMs: 1, maxMs: 1 } },
    );
    const error = await prom.catch((e) => e);
    expect(error).toBeInstanceOf(ConnectionTimeoutError);
    expect(fetchCount).toBe(2);
});

test("trigger a ServerOverloadError when response carries a non-JSON content-type", async () => {
    mockFetch(
        () =>
            new Response("<html>pool full</html>", {
                status: 500,
                headers: { "Content-Type": "text/html" },
            }),
    );

    await expect(rpc("/test/")).rejects.toThrow(ServerOverloadError);
});

test("502/503/504 proxy statuses are ServerOverloadError (earn the backoff floor)", async () => {
    for (const status of [502, 503, 504]) {
        mockFetch(() => new Response("", { status }));
        const error = await rpc("/test/").catch((e) => e);
        expect(error).toBeInstanceOf(ServerOverloadError);
        expect(error).toBeInstanceOf(ConnectionLostError);
        expect(error.status).toBe(status);
    }
});

test("ServerOverloadError is also a ConnectionLostError (backward compatibility)", async () => {
    mockFetch(
        () =>
            new Response("<html/>", {
                status: 500,
                headers: { "Content-Type": "text/html; charset=utf-8" },
            }),
    );

    await expect(rpc("/test/")).rejects.toThrow(ConnectionLostError);
});

test("trigger a ConnectionLostError when response says JSON but body is unparseable", async () => {
    mockFetch(
        () =>
            new Response("<h...", {
                status: 500,
                headers: { "Content-Type": "application/json" },
            }),
    );

    await expect(rpc("/test/")).rejects.toThrow(ConnectionLostError);
});

test("no content-type header falls back to ConnectionLostError (preserves prior behavior)", async () => {
    mockFetch(() => {
        const r = new Response("<h...", { status: 500 });
        r.headers.delete("content-type");
        return r;
    });

    await expect(rpc("/test/")).rejects.toThrow(ConnectionLostError);
});

test("non-JSON response with a non-5xx status is an InvalidResponseError", async () => {
    mockFetch(
        () =>
            new Response("<html>login page</html>", {
                status: 200,
                headers: { "Content-Type": "text/html" },
            }),
    );

    await expect(rpc("/test/")).rejects.toThrow(InvalidResponseError);
});

test("a non-JSON non-5xx response is an InvalidResponseError, NOT a ConnectionLostError", async () => {
    mockFetch(
        () =>
            new Response("<html>not found</html>", {
                status: 404,
                headers: { "Content-Type": "text/html" },
            }),
    );

    const error = await rpc("/test/").catch((e) => e);
    expect(error).toBeInstanceOf(InvalidResponseError);
    expect(error).not.toBeInstanceOf(ConnectionLostError);
    expect(error.retryable).toBe(false);
});

test("retryability is behaviour-as-data on the error, not its class", () => {
    expect(new ConnectionLostError("/x").retryable).toBe(true);
    expect(new ConnectionTimeoutError("/x", 100).retryable).toBe(true);
    expect(new ServerOverloadError("/x", 503).retryable).toBe(true);
    expect(new InvalidResponseError("/x", 404).retryable).toBe(false);
    expect(new ConnectionAbortedError().retryable).toBe(false);
    expect(new RPCError().retryable).toBe(false);
});

test("unparseable JSON body with a non-5xx status is an InvalidResponseError", async () => {
    mockFetch(
        () =>
            new Response("", {
                status: 200,
                headers: { "Content-Type": "application/json" },
            }),
    );

    await expect(rpc("/test/")).rejects.toThrow(InvalidResponseError);
});

/**
 * @param {string} url
 * @returns {Response}
 */
function responseWithBrokenBodyStream(url) {
    const response = new Response("{}", {
        status: 200,
        headers: { "Content-Type": "application/json" },
    });
    response.json = () => Promise.reject(new TypeError(`Failed to fetch ${url}`));
    return response;
}

test("a transfer cut mid-body is a ConnectionLostError, not an InvalidResponseError", async () => {
    mockFetch(() => responseWithBrokenBodyStream("/test/"));

    const error = await rpc("/test/").catch((e) => e);
    expect(error).toBeInstanceOf(ConnectionLostError);
    expect(error).not.toBeInstanceOf(InvalidResponseError);
});

test("Retry: a transfer cut mid-body is retried like any other transport failure", async () => {
    let fetchCount = 0;
    mockFetch(() => {
        fetchCount++;
        if (fetchCount === 1) {
            return responseWithBrokenBodyStream("/test/");
        }
        return { result: "recovered" };
    });

    const prom = rpc("/test/", {}, { retry: { retries: 1, baseMs: 1, maxMs: 1 } });
    expect(await prom).toBe("recovered");
    expect(fetchCount).toBe(2);
});

test("Retry: InvalidResponseError is never retried", async () => {
    let fetchCount = 0;
    mockFetch(() => {
        fetchCount++;
        return new Response("<html>login page</html>", {
            status: 200,
            headers: { "Content-Type": "text/html" },
        });
    });

    const prom = rpc("/test/", {}, { retry: 3 });
    await expect(prom).rejects.toThrow(InvalidResponseError);
    expect(fetchCount).toBe(1);
});

test("rpc can send additional headers", async () => {
    mockFetch((url, settings) => {
        expect(settings.headers).toEqual(
            new Headers([
                ["Content-Type", "application/json"],
                ["Hello", "World"],
            ]),
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
            "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b",
        ),
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

test("Dedup: concurrent identical rpcs share one fetch, not one promise", async () => {
    mockFetch(() => {
        expect.step("Fetch");
        return { result: { x: 1 } };
    });

    const p1 = rpc("/test/", {}, { dedup: true });
    const p2 = rpc("/test/", {}, { dedup: true });
    const p3 = rpc("/test/", {}, { dedup: true });

    expect(p1).not.toBe(p2);
    expect(p2).not.toBe(p3);

    const [r1, r2, r3] = await Promise.all([p1, p2, p3]);
    expect(r1).toEqual({ x: 1 });
    expect(r2).toEqual({ x: 1 });
    expect(r3).toEqual({ x: 1 });
    expect.verifySteps(["Fetch"]);
});

test("Dedup: different (url, params) do not collide", async () => {
    mockFetch((_, { body }) => {
        const id = JSON.parse(String(body)).params.id;
        expect.step(`Fetch:${id}`);
        return { result: { id } };
    });

    const p1 = rpc("/test/", { id: 1 }, { dedup: true });
    const p2 = rpc("/test/", { id: 2 }, { dedup: true });
    expect(p1).not.toBe(p2);

    await Promise.all([p1, p2]);
    expect.verifySteps(["Fetch:1", "Fetch:2"]);
});

test("Dedup: post-settle call fires fresh (entry evicted)", async () => {
    mockFetch(() => {
        expect.step("Fetch");
        return { result: true };
    });

    await rpc("/test/", {}, { dedup: true });
    await rpc("/test/", {}, { dedup: true });
    expect.verifySteps(["Fetch", "Fetch"]);
});

test("Dedup: error path also evicts so subsequent calls retry", async () => {
    mockFetch(() => {
        expect.step("Fetch");
        return new Response("<h...", { status: 500 });
    });

    const p1 = rpc("/test/", {}, { dedup: true });
    const p2 = rpc("/test/", {}, { dedup: true });

    await expect(p1).rejects.toThrow(ConnectionLostError);
    await expect(p2).rejects.toThrow(ConnectionLostError);
    expect.verifySteps(["Fetch"]);

    await expect(rpc("/test/", {}, { dedup: true })).rejects.toThrow(
        ConnectionLostError,
    );
    expect.verifySteps(["Fetch"]);
});

test("Dedup: silent abort evicts the inflight entry (regression)", async () => {
    let fetchCount = 0;
    mockFetch(() => {
        fetchCount++;
        expect.step(`Fetch:${fetchCount}`);
        if (fetchCount === 1) {
            return new Promise(() => {});
        }
        return { result: { ok: true } };
    });

    const p1 = rpc("/test/", {}, { dedup: true });
    p1.abort(false);

    const p2 = rpc("/test/", {}, { dedup: true });
    expect(p2).not.toBe(p1);
    expect(await p2).toEqual({ ok: true });
    expect.verifySteps(["Fetch:1", "Fetch:2"]);
});

test("Dedup composes with cache: cache hit skips the fetch", async () => {
    rpc.setCache(
        new RPCCache(
            "mockRpcDedup",
            1,
            "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b",
        ),
    );
    mockFetch(() => {
        expect.step("Fetch");
        return { result: { x: 42 } };
    });

    expect(await rpc("/test/", {}, { cache: true })).toEqual({ x: 42 });
    expect.verifySteps(["Fetch"]);

    const p1 = rpc("/test/", {}, { cache: true, dedup: true });
    const p2 = rpc("/test/", {}, { cache: true, dedup: true });
    await Promise.all([p1, p2]);
    expect.verifySteps([]);
});

test("Dedup + cache: callers with different callbacks are not deduped together", async () => {
    rpc.setCache(
        new RPCCache(
            "mockRpcDedupCb",
            1,
            "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b",
        ),
    );
    mockFetch(() => {
        expect.step("Fetch");
        return { result: { x: 1 } };
    });

    const p1 = rpc(
        "/test/",
        {},
        { dedup: true, cache: { update: "always", callback: () => {} } },
    );
    const p2 = rpc(
        "/test/",
        {},
        { dedup: true, cache: { update: "always", callback: () => {} } },
    );
    expect(p1).not.toBe(p2);
    expect(await p1).toEqual({ x: 1 });
    expect(await p2).toEqual({ x: 1 });
    expect.verifySteps(["Fetch"]);
});

test("Dedup: differing settings do not leak silent to a non-silent caller", async () => {
    mockFetch(() => {
        expect.step("Fetch");
        return { result: true };
    });
    const requestSilentFlags = [];
    onRpcRequest(({ detail }) =>
        requestSilentFlags.push(Boolean(detail.settings.silent)),
    );

    const pSilent = rpc("/test/", {}, { dedup: true, silent: true });
    const pLoud = rpc("/test/", {}, { dedup: true });

    expect(pSilent).not.toBe(pLoud);

    await Promise.all([pSilent, pLoud]);

    expect.verifySteps(["Fetch", "Fetch"]);
    expect(requestSilentFlags).toEqual([true, false]);
});

test("Dedup: identical settings still share one fetch", async () => {
    mockFetch(() => {
        expect.step("Fetch");
        return { result: { ok: true } };
    });

    const p1 = rpc("/test/", {}, { dedup: true, silent: true });
    const p2 = rpc("/test/", {}, { dedup: true, silent: true });
    expect(p1).not.toBe(p2);

    expect(await Promise.all([p1, p2])).toEqual([{ ok: true }, { ok: true }]);
    expect.verifySteps(["Fetch"]);
});

test("Cache: abort(false) on a cache-miss rpc exposes abort and does not throw", async () => {
    rpc.setCache(
        new RPCCache(
            "mockRpcCacheAbortMiss",
            1,
            "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b",
        ),
    );
    mockFetch(() => new Promise(() => {}));

    const prom = rpc("/test/", {}, { cache: true });
    expect(prom.abort).toBeInstanceOf(Function);
    await tick();
    expect(() => prom.abort(false)).not.toThrow();
});

test("Cache: abort on a cache hit is a safe no-op", async () => {
    rpc.setCache(
        new RPCCache(
            "mockRpcCacheAbortHit",
            1,
            "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b",
        ),
    );
    mockFetch(() => {
        expect.step("Fetch");
        return { result: { x: 7 } };
    });

    expect(await rpc("/test/", {}, { cache: true })).toEqual({ x: 7 });
    expect.verifySteps(["Fetch"]);

    const prom = rpc("/test/", {}, { cache: true });
    expect(prom.abort).toBeInstanceOf(Function);
    expect(() => prom.abort(false)).not.toThrow();
    expect(await prom).toEqual({ x: 7 });
    expect.verifySteps([]);
});

test("abort after settle does not emit a second RPC:RESPONSE", async () => {
    mockFetch(() => ({ result: { ok: true } }));
    onRpcResponse(() => expect.step("RESPONSE"));

    const prom = rpc("/test/");
    expect(await prom).toEqual({ ok: true });
    expect.verifySteps(["RESPONSE"]);

    expect(() => prom.abort()).not.toThrow();
    expect(() => prom.abort(false)).not.toThrow();
    await tick();
    expect.verifySteps([]);
});

test("abort after an RPCError settle does not emit a second RPC:RESPONSE", async () => {
    mockFetch(() => ({ error: { code: 200, message: "Odoo Server Error", data: {} } }));
    onRpcResponse(() => expect.step("RESPONSE"));

    const prom = rpc("/test/");
    await expect(prom).rejects.toThrow(RPCError);
    expect.verifySteps(["RESPONSE"]);

    expect(() => prom.abort()).not.toThrow();
    expect(() => prom.abort(false)).not.toThrow();
    await tick();
    expect.verifySteps([]);
});

test("abort after a network-failure settle does not emit a second RPC:RESPONSE", async () => {
    mockFetch(() => {
        throw new TypeError("NetworkError when attempting to fetch resource.");
    });
    onRpcResponse(() => expect.step("RESPONSE"));

    const prom = rpc("/test/");
    await expect(prom).rejects.toThrow(ConnectionLostError);
    expect.verifySteps(["RESPONSE"]);

    expect(() => prom.abort()).not.toThrow();
    expect(() => prom.abort(false)).not.toThrow();
    await tick();
    expect.verifySteps([]);
});

test("Retry: abort while an attempt is in flight rejects once", async () => {
    mockFetch(() => new Promise(() => {}));
    onRpcResponse(({ detail }) =>
        expect.step("error" in detail ? "RESPONSE(ko)" : "RESPONSE(ok)"),
    );

    const prom = rpc("/test/", {}, { retry: 3 });
    prom.abort();
    await expect(prom).rejects.toThrow(ConnectionAbortedError);
    expect.verifySteps(["RESPONSE(ko)"]);
});

test("Retry: abort during backoff cancels the scheduled retry", async () => {
    let fetchCount = 0;
    mockFetch(() => {
        fetchCount++;
        expect.step(`Fetch:${fetchCount}`);
        return new Response("<h...", {
            status: 500,
            headers: { "Content-Type": "application/json" },
        });
    });

    const prom = rpc(
        "/test/",
        {},
        { retry: { retries: 5, baseMs: 100000, maxMs: 100000 } },
    );
    await tick();
    await tick();
    expect.verifySteps(["Fetch:1"]);

    prom.abort(false);
    await runAllTimers();
    await tick();
    expect.verifySteps([]);
});

test("abort(false) drops the request WITHOUT ever settling the promise", async () => {
    mockFetch(() => new Promise(() => {}));

    const prom = rpc("/test/", {});
    let settled = "pending";
    prom.then(
        () => (settled = "resolved"),
        () => (settled = "rejected"),
    );

    prom.abort(false);
    await runAllTimers();
    await tick();
    await tick();
    expect(settled).toBe("pending", {
        message: "abort(false) leaves the promise unsettled forever",
    });

    const rejecting = rpc("/test/", {});
    let rejectedWith = null;
    rejecting.catch((error) => (rejectedWith = error));
    rejecting.abort();
    await tick();
    await tick();
    expect(rejectedWith).toBeInstanceOf(ConnectionAbortedError);
});

test("envelope version: list result gets __version attached when parsed.version is present", async () => {
    mockFetch(() => ({
        result: [{ id: 1 }, { id: 2 }],
        version: "abc123def456",
    }));
    const result = await rpc("/test/");
    expect(result).toEqual([{ id: 1 }, { id: 2 }]);
    expect(result.__version).toBe("abc123def456");
});

test("envelope version: dict result gets __version attached when parsed.version is present", async () => {
    mockFetch(() => ({
        result: { records: [{ id: 1 }], length: 1 },
        version: "v789",
    }));
    const result = await rpc("/test/");
    expect(result.__version).toBe("v789");
});

test("envelope version: in-payload __version wins over envelope sibling", async () => {
    mockFetch(() => ({
        result: { records: [], __version: "in-payload-wins" },
        version: "envelope-loses",
    }));
    const result = await rpc("/test/");
    expect(result.__version).toBe("in-payload-wins");
});

test("envelope version: absent parsed.version leaves result unchanged", async () => {
    mockFetch(() => ({ result: [{ id: 1 }] }));
    const result = await rpc("/test/");
    expect(result).toEqual([{ id: 1 }]);
    expect(result.__version).toBe(undefined);
});

test("envelope version: primitive result is not mutated (cannot attach property)", async () => {
    mockFetch(() => ({ result: 42, version: "v1" }));
    const result = await rpc("/test/");
    expect(result).toBe(42);
});

test("envelope version: null result is not mutated", async () => {
    mockFetch(() => ({ result: null, version: "v1" }));
    const result = await rpc("/test/");
    expect(result).toBe(null);
});

describe("CLEAR-CACHES bus handling", () => {
    function withStubCache() {
        const calls = { invalidate: [], invalidateByModel: [] };
        const cache = new RPCCache("mockRpc", 1);
        patchWithCleanup(cache, {
            invalidate: (tables) => {
                calls.invalidate.push(tables);
            },
            invalidateByModel: (tables, model) => {
                calls.invalidateByModel.push([tables, model]);
            },
        });
        rpc.setCache(cache);
        after(() => rpc.setCache(undefined));
        return calls;
    }

    test("purgeCacheStorage delegates to the cache, and no-ops without one", async () => {
        let purged = 0;
        const cache = new RPCCache("mockRpc", 1);
        patchWithCleanup(cache, {
            removeStorage: async () => {
                purged++;
            },
        });
        rpc.setCache(cache);
        after(() => rpc.setCache(undefined));

        await rpc.purgeCacheStorage();
        expect(purged).toBe(1);

        rpc.setCache(undefined);
        await rpc.purgeCacheStorage();
        expect(purged).toBe(1);
    });

    test("object detail WITHOUT a model invalidates the named tables (not the object)", () => {
        const calls = withStubCache();
        rpcBus.dispatchEvent(
            new CustomEvent("CLEAR-CACHES", {
                detail: { tables: ["web_read", "web_search_read"] },
            }),
        );
        expect(calls.invalidate).toEqual([["web_read", "web_search_read"]]);
        expect(calls.invalidateByModel).toEqual([]);
    });

    test("object detail WITH a model invalidates by model", () => {
        const calls = withStubCache();
        rpcBus.dispatchEvent(
            new CustomEvent("CLEAR-CACHES", {
                detail: { model: "res.partner", tables: ["web_read"] },
            }),
        );
        expect(calls.invalidateByModel).toEqual([[["web_read"], "res.partner"]]);
        expect(calls.invalidate).toEqual([]);
    });

    test("a bare table name string still invalidates that table", () => {
        const calls = withStubCache();
        rpcBus.dispatchEvent(new CustomEvent("CLEAR-CACHES", { detail: "web_read" }));
        expect(calls.invalidate).toEqual(["web_read"]);
    });
});

const RPC_CACHE_SECRET =
    "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b";

test("Cache: aborting a cache joiner rejects only that caller", async () => {
    rpc.setCache(new RPCCache("mockRpc", 1, RPC_CACHE_SECRET));
    after(() => rpc.setCache(undefined));

    const fetchDef = new Deferred();
    let fetchCount = 0;
    mockFetch(() => {
        fetchCount++;
        return fetchDef;
    });

    const initiator = rpc("/test/", {}, { cache: true });
    const joiner = rpc("/test/", {}, { cache: true });

    let initiatorState = "pending";
    initiator.then(
        () => (initiatorState = "resolved"),
        () => (initiatorState = "rejected"),
    );
    let joinerState = "pending";
    joiner.then(
        () => (joinerState = "resolved"),
        (/** @type {Error} */ e) => (joinerState = e.constructor.name),
    );

    await tick();
    expect(fetchCount).toBe(1);

    joiner.abort(true);
    await tick();
    expect(joinerState).toBe("ConnectionAbortedError");
    expect(initiatorState).toBe("pending");

    fetchDef.resolve({ result: { ok: 1 } });
    expect(await initiator).toEqual({ ok: 1 });
});

test("Cache: a joiner aborted with abort(false) swallows a later shared rejection", async () => {
    rpc.setCache(new RPCCache("mockRpc", 1, RPC_CACHE_SECRET));
    after(() => rpc.setCache(undefined));

    const fetchDef = new Deferred();
    mockFetch(() => fetchDef);

    const initiator = rpc("/test/", {}, { cache: true });
    const joiner = rpc("/test/", {}, { cache: true });

    let initiatorState = "pending";
    initiator.then(
        () => (initiatorState = "resolved"),
        (/** @type {Error} */ e) => (initiatorState = e.constructor.name),
    );
    let joinerState = "pending";
    joiner.then(
        () => (joinerState = "resolved"),
        (/** @type {Error} */ e) => (joinerState = e.constructor.name),
    );

    await tick();

    joiner.abort(false);
    await tick();
    expect(joinerState).toBe("pending");

    const r = new Response("<h...", { status: 500 });
    r.headers.delete("content-type");
    fetchDef.resolve(r);
    await tick();
    await tick();

    expect(initiatorState).toBe("ConnectionLostError");
    expect(joinerState).toBe("pending");
});

test("Cache: aborting a joiner stops its update:'always' callback firing after teardown", async () => {
    rpc.setCache(new RPCCache("mockRpc", 1, RPC_CACHE_SECRET));
    after(() => rpc.setCache(undefined));

    const fetchDef = new Deferred();
    let fetchCount = 0;
    mockFetch(() => {
        fetchCount++;
        return fetchDef;
    });

    const initiator = rpc(
        "/test/",
        {},
        {
            cache: {
                update: "always",
                callback: () => expect.step("initiator callback"),
            },
        },
    );
    const joiner = rpc(
        "/test/",
        {},
        {
            cache: { update: "always", callback: () => expect.step("joiner callback") },
        },
    );
    joiner.catch(() => {});

    await tick();
    expect(fetchCount).toBe(1);

    joiner.abort(true);
    await tick();

    fetchDef.resolve({ result: { ok: 1 } });
    expect(await initiator).toEqual({ ok: 1 });
    await tick();
    expect.verifySteps(["initiator callback"]);
});

test("Cache: aborting the initiator rejects it (control)", async () => {
    rpc.setCache(new RPCCache("mockRpc", 1, RPC_CACHE_SECRET));
    after(() => rpc.setCache(undefined));
    mockFetch(() => new Promise(() => {}));

    const initiator = rpc("/test/", {}, { cache: true });
    initiator.abort(true);
    await expect(initiator).rejects.toThrow(new ConnectionAbortedError());
});

test("RPC:RESPONSE carries the url, like RPC:REQUEST", async () => {
    const seen = [];
    onRpcRequest(({ detail }) => seen.push(["request", detail.url]));
    onRpcResponse(({ detail }) => seen.push(["response", detail.url]));

    mockFetch(() => ({ result: 1 }));
    await rpc("/web/session/get_session_info");
    expect(seen).toEqual([
        ["request", "/web/session/get_session_info"],
        ["response", "/web/session/get_session_info"],
    ]);

    seen.length = 0;
    mockFetch(() => ({ error: { code: 200, message: "boom", data: {} } }));
    await rpc("/web/action/load").catch(() => {});
    expect(seen).toEqual([
        ["request", "/web/action/load"],
        ["response", "/web/action/load"],
    ]);

    seen.length = 0;
    mockFetch(() => new Promise(() => {}));
    const prom = rpc("/web/dataset/call_kw/foo/bar");
    prom.abort(false);
    expect(seen).toEqual([
        ["request", "/web/dataset/call_kw/foo/bar"],
        ["response", "/web/dataset/call_kw/foo/bar"],
    ]);
});

test("Dedup: one caller's abort does not cancel the others", async () => {
    mockFetch(async () => {
        expect.step("Fetch");
        await tick();
        return { result: { x: 1 } };
    });

    const p1 = rpc("/test/", {}, { dedup: true });
    const p2 = rpc("/test/", {}, { dedup: true });
    /** @type {any} */ (p1).abort();

    await expect(p1).rejects.toThrow(ConnectionAbortedError);
    expect(await p2).toEqual({ x: 1 });
    expect.verifySteps(["Fetch"]);
});

test("Dedup: the shared request is cancelled once the last caller leaves", async () => {
    let fetchCount = 0;
    mockFetch(() => {
        fetchCount++;
        expect.step(`Fetch:${fetchCount}`);
        if (fetchCount === 1) {
            return new Promise(() => {});
        }
        return { result: { ok: true } };
    });

    const p1 = rpc("/test/", {}, { dedup: true });
    const p2 = rpc("/test/", {}, { dedup: true });
    p1.then(
        () => {},
        () => {},
    );
    p2.then(
        () => {},
        () => {},
    );
    /** @type {any} */ (p1).abort();
    expect.verifySteps(["Fetch:1"]);

    const p3 = rpc("/test/", {}, { dedup: true });
    p3.then(
        () => {},
        () => {},
    );
    expect.verifySteps([]);

    /** @type {any} */ (p2).abort();
    /** @type {any} */ (p3).abort();
    expect(await rpc("/test/", {}, { dedup: true })).toEqual({ ok: true });
    expect.verifySteps(["Fetch:2"]);
});

test("Retry: the server-overload backoff floor survives a smaller maxMs", async () => {
    /** @type {number[]} */
    const delays = [];
    const realSetTimeout = browser.setTimeout;
    patchWithCleanup(browser, {
        setTimeout(fn, delay, ...rest) {
            delays.push(delay);
            return realSetTimeout(fn, delay, ...rest);
        },
    });

    let fetchCount = 0;
    mockFetch(() => {
        fetchCount++;
        return new Response("<html>overloaded</html>", { status: 503 });
    });

    const prom = rpc("/test/", {}, { retry: { retries: 1, baseMs: 1, maxMs: 5 } });
    prom.catch(() => {});
    await tick();
    await tick();
    expect(fetchCount).toBe(1);
    expect(delays).toHaveLength(1);
    expect(delays[0]).toBeGreaterThan(999, {
        message: `scheduled retry after ${delays[0]}ms; the floor is 1000ms`,
    });

    prom.abort(false);
    await runAllTimers();
});

test("Retry: a normal retryable error still honours maxMs", async () => {
    /** @type {number[]} */
    const delays = [];
    const realSetTimeout = browser.setTimeout;
    patchWithCleanup(browser, {
        setTimeout(fn, delay, ...rest) {
            delays.push(delay);
            return realSetTimeout(fn, delay, ...rest);
        },
    });

    mockFetch(() => Promise.reject(new TypeError("Failed to fetch")));

    const prom = rpc("/test/", {}, { retry: { retries: 1, baseMs: 1, maxMs: 5 } });
    prom.catch(() => {});
    await tick();
    await tick();
    expect(delays).toHaveLength(1);
    expect(delays[0]).toBeLessThan(6, {
        message: "no ServerOverloadError: the cap applies unchanged",
    });

    prom.abort(false);
    await runAllTimers();
});

/**
 * @param {string} name
 * @returns {void}
 */
function useScratchCache(name) {
    rpc.setCache(
        new RPCCache(
            name,
            1,
            "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b",
        ),
    );
}

/** @returns {{ count: () => number }} */
function neverSettlingFetch() {
    let count = 0;
    patchBrowserFetch((_url, { signal }) => {
        count++;
        return new Promise((_resolve, reject) => {
            signal.addEventListener("abort", () => reject(signal.reason));
        });
    });
    return { count: () => count };
}

test("signal + cache: aborting one caller leaves a joiner that passed no signal", async () => {
    useScratchCache("mockRpcSignalCacheJoin");
    const fetches = neverSettlingFetch();

    const controller = new AbortController();
    const pAborted = rpc("/test/", {}, { cache: true, signal: controller.signal });
    await tick();
    const pInnocent = rpc("/test/", {}, { cache: true });
    await tick();
    expect(fetches.count()).toBe(1, {
        message: "the second caller joined rather than issuing its own request",
    });

    controller.abort();
    await runAllTimers();

    await expect(pAborted).rejects.toThrow(ConnectionAbortedError);
    let innocentSettled = false;
    pInnocent.then(
        () => (innocentSettled = true),
        () => (innocentSettled = true),
    );
    await tick();
    expect(innocentSettled).toBe(false, {
        message: "the joiner still waits on a request it never asked to cancel",
    });
    pInnocent.abort(false);
    await runAllTimers();
});

test("signal + cache: the last caller out does tear the request down", async () => {
    useScratchCache("mockRpcSignalCacheLastOut");
    const fetches = neverSettlingFetch();

    const first = new AbortController();
    const second = new AbortController();
    const p1 = rpc("/test/", {}, { cache: true, signal: first.signal });
    await tick();
    const p2 = rpc("/test/", {}, { cache: true, signal: second.signal });
    await tick();
    expect(fetches.count()).toBe(1);

    const errors = [];
    p1.catch((e) => errors.push(e.constructor.name));
    p2.catch((e) => errors.push(e.constructor.name));

    first.abort();
    await runAllTimers();
    second.abort();
    await runAllTimers();

    expect(errors).toEqual(["ConnectionAbortedError", "ConnectionAbortedError"]);
});

test("signal + dedup: the signal detaches one subscriber, not the group", async () => {
    const fetches = neverSettlingFetch();

    const controller = new AbortController();
    const pAborted = rpc("/test/", {}, { dedup: true, signal: controller.signal });
    await tick();
    const pInnocent = rpc("/test/", {}, { dedup: true });
    await tick();
    expect(fetches.count()).toBe(1, { message: "deduplicated onto one request" });

    controller.abort();
    await runAllTimers();

    await expect(pAborted).rejects.toThrow(ConnectionAbortedError);
    let innocentSettled = false;
    pInnocent.then(
        () => (innocentSettled = true),
        () => (innocentSettled = true),
    );
    await tick();
    expect(innocentSettled).toBe(false);
    pInnocent.abort(false);
    await runAllTimers();
});

test("signal + dedup: two callers with different signals still share one request", async () => {
    const fetches = neverSettlingFetch();

    const a = new AbortController();
    const b = new AbortController();
    const p1 = rpc("/test/", {}, { dedup: true, signal: a.signal });
    const p2 = rpc("/test/", {}, { dedup: true, signal: b.signal });
    p1.catch(() => {});
    p2.catch(() => {});
    await tick();
    expect(fetches.count()).toBe(1, {
        message: "the signal is not part of the dedup fingerprint",
    });
    a.abort();
    b.abort();
    await runAllTimers();
});

test("signal: an already-aborted signal aborts the caller's handle at once", async () => {
    useScratchCache("mockRpcSignalPreAborted");
    neverSettlingFetch();

    const controller = new AbortController();
    controller.abort();
    await expect(
        rpc("/test/", {}, { cache: true, signal: controller.signal }),
    ).rejects.toThrow(ConnectionAbortedError);
});

test("signal: unshared requests still abort the fetch itself", async () => {
    const fetches = neverSettlingFetch();
    const controller = new AbortController();
    const prom = rpc("/test/", {}, { signal: controller.signal });
    await tick();
    controller.abort();
    const error = await prom.catch((e) => e);
    expect(error).toBeInstanceOf(ConnectionAbortedError);
    expect(fetches.count()).toBe(1);
});
