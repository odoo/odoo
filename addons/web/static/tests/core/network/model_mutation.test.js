// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { RpcEvent } from "@web/core/events";
import { onModelMutation, UPDATE_METHODS } from "@web/core/network/model_mutation";
import { ConnectionLostError, rpcBus, RPCError } from "@web/core/network/rpc";

describe.current.tags("headless");

/**
 * @param {string} model
 * @param {string} method
 * @param {any} [error]
 */
function fire(model, method, error) {
    rpcBus.trigger(RpcEvent.RESPONSE, {
        data: { params: { model, method } },
        url: "/web/dataset/call_kw",
        settings: { silent: true },
        error,
    });
}

function serverRejection() {
    const error = new RPCError("Access denied");
    error.exceptionName = "odoo.exceptions.AccessError";
    return error;
}

test("fires for every UPDATE_METHOD on a watched model", () => {
    const seen = [];
    const dispose = onModelMutation(["res.partner"], (info) => seen.push(info.method));
    for (const method of UPDATE_METHODS) {
        fire("res.partner", method);
    }
    dispose();
    expect(seen).toEqual(UPDATE_METHODS);
});

test("ignores unwatched models and unwatched methods", () => {
    const seen = [];
    const dispose = onModelMutation(["res.partner"], (info) => seen.push(info));
    fire("res.users", "write");
    fire("res.partner", "read");
    fire("res.partner", "web_search_read");
    dispose();
    expect(seen).toEqual([]);
});

test("a model predicate is honoured", () => {
    const seen = [];
    const dispose = onModelMutation(
        (model) => model.startsWith("ir."),
        (info) => seen.push(info.model),
    );
    fire("ir.ui.view", "write");
    fire("res.partner", "write");
    fire("ir.access", "unlink");
    dispose();
    expect(seen).toEqual(["ir.ui.view", "ir.access"]);
});

test("a server rejection is SKIPPED: the transaction rolled back", () => {
    const seen = [];
    const dispose = onModelMutation(["res.partner"], (info) => seen.push(info));
    fire("res.partner", "write", serverRejection());
    dispose();
    expect(seen).toEqual([]);
});

test("a duck-typed RPC_ERROR is skipped too", () => {
    const seen = [];
    const dispose = onModelMutation(["res.partner"], (info) => seen.push(info));
    fire("res.partner", "write", { name: "RPC_ERROR", message: "boom" });
    dispose();
    expect(seen).toEqual([]);
});

test("a LOST response FIRES: the write may have committed", () => {
    const seen = [];
    const dispose = onModelMutation(["res.partner"], (info) => seen.push(info));
    fire("res.partner", "write", new ConnectionLostError("/web/dataset/call_kw"));
    dispose();
    expect(seen).toHaveLength(1);
    expect(seen[0].error).toBeInstanceOf(ConnectionLostError);
});

test("successOnly drops the lost-response case as well", () => {
    const seen = [];
    const dispose = onModelMutation(["res.partner"], (info) => seen.push(info), {
        successOnly: true,
    });
    fire("res.partner", "write", new ConnectionLostError("/web/dataset/call_kw"));
    fire("res.partner", "write", serverRejection());
    fire("res.partner", "write");
    dispose();
    expect(seen).toHaveLength(1);
    expect(seen[0].error).toBe(undefined);
});

test("methods narrows (and replaces) the watched set", () => {
    const seen = [];
    const dispose = onModelMutation(
        ["base.language.install"],
        (info) => seen.push(info.method),
        { methods: ["action_install_lang"] },
    );
    fire("base.language.install", "action_install_lang");
    fire("base.language.install", "write");
    dispose();
    expect(seen).toEqual(["action_install_lang"]);
});

test("a malformed event is ignored rather than thrown out of the bus", () => {
    const seen = [];
    const dispose = onModelMutation(["res.partner"], (info) => seen.push(info));
    rpcBus.trigger(RpcEvent.RESPONSE, null);
    rpcBus.trigger(RpcEvent.RESPONSE, {});
    rpcBus.trigger(RpcEvent.RESPONSE, { data: {} });
    rpcBus.trigger(RpcEvent.RESPONSE, { data: { params: {} } });
    rpcBus.trigger(RpcEvent.RESPONSE, {
        data: { params: { model: 42, method: "write" } },
    });
    dispose();
    expect(seen).toEqual([]);
});

test("the disposer really detaches the listener", () => {
    const seen = [];
    const dispose = onModelMutation(["res.partner"], (info) => seen.push(info));
    fire("res.partner", "write");
    dispose();
    fire("res.partner", "write");
    dispose();
    expect(seen).toHaveLength(1);
});
