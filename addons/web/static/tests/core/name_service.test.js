import { after, describe, expect, test } from "@odoo/hoot";
import {
    defineModels,
    getService,
    makeMockEnv,
    models,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { ERROR_INACCESSIBLE_OR_MISSING } from "@web/core/name_service";
import { rpcBus } from "@web/core/network/rpc";

class Dev extends models.Model {
    _name = "dev";
    _rec_name = "display_name";
    _records = [
        { id: 1, display_name: "Julien" },
        { id: 2, display_name: "Pierre" },
    ];
}

class PO extends models.Model {
    _name = "po";
    _rec_name = "display_name";
    _records = [{ id: 1, display_name: "Damien" }];
}

defineModels([Dev, PO]);

describe.current.tags("headless");

test("single loadDisplayNames", async () => {
    await makeMockEnv();
    const displayNames = await getService("name").loadDisplayNames("dev", [1, 2]);
    expect(displayNames).toEqual({ 1: "Julien", 2: "Pierre" });
});

test("loadDisplayNames is done in silent mode", async () => {
    await makeMockEnv();

    const onRPCRequest = ({ detail }) => {
        const silent = detail.settings.silent ? "(silent)" : "";
        expect.step(`RPC:REQUEST${silent}`);
    };
    rpcBus.addEventListener("RPC:REQUEST", onRPCRequest);
    after(() => rpcBus.removeEventListener("RPC:REQUEST", onRPCRequest));

    await getService("name").loadDisplayNames("dev", [1]);
    expect.verifySteps(["RPC:REQUEST(silent)"]);
});

test("single loadDisplayNames following addDisplayNames", async () => {
    await makeMockEnv();
    onRpc(({ model, method, kwargs }) => {
        expect.step(`${model}:${method}:${kwargs.domain[0][2]}`);
    });

    getService("name").addDisplayNames("dev", { 1: "JUM", 2: "PIPU" });
    const displayNames = await getService("name").loadDisplayNames("dev", [1, 2]);
    expect(displayNames).toEqual({ 1: "JUM", 2: "PIPU" });
    expect.verifySteps([]);
});

test("single loadDisplayNames following addDisplayNames (2)", async () => {
    await makeMockEnv();
    onRpc(({ model, method, kwargs }) => {
        expect.step(`${model}:${method}:${kwargs.domain[0][2]}`);
    });

    getService("name").addDisplayNames("dev", { 1: "JUM" });
    const displayNames = await getService("name").loadDisplayNames("dev", [1, 2]);
    expect(displayNames).toEqual({ 1: "JUM", 2: "Pierre" });
    expect.verifySteps(["dev:web_search_read:2"]);
});

test("loadDisplayNames in batch", async () => {
    await makeMockEnv();
    onRpc(({ model, method, kwargs }) => {
        expect.step(`${model}:${method}:${kwargs.domain[0][2]}`);
    });

    const loadPromise1 = getService("name").loadDisplayNames("dev", [1]);
    expect.verifySteps([]);
    const loadPromise2 = getService("name").loadDisplayNames("dev", [2]);
    expect.verifySteps([]);

    const [displayNames1, displayNames2] = await Promise.all([loadPromise1, loadPromise2]);
    expect(displayNames1).toEqual({ 1: "Julien" });
    expect(displayNames2).toEqual({ 2: "Pierre" });
    expect.verifySteps(["dev:web_search_read:1,2"]);
});

test("loadDisplayNames on different models", async () => {
    await makeMockEnv();
    onRpc(({ model, method, kwargs }) => {
        expect.step(`${model}:${method}:${kwargs.domain[0][2]}`);
    });

    const loadPromise1 = getService("name").loadDisplayNames("dev", [1]);
    expect.verifySteps([]);
    const loadPromise2 = getService("name").loadDisplayNames("po", [1]);
    expect.verifySteps([]);

    const [displayNames1, displayNames2] = await Promise.all([loadPromise1, loadPromise2]);
    expect(displayNames1).toEqual({ 1: "Julien" });
    expect(displayNames2).toEqual({ 1: "Damien" });

    expect.verifySteps(["dev:web_search_read:1", "po:web_search_read:1"]);
});

test("invalid id", async () => {
    await makeMockEnv();
    try {
        await getService("name").loadDisplayNames("dev", ["a"]);
    } catch (error) {
        expect(error.message).toBe("Invalid ID: a");
    }
});

test("inaccessible or missing id", async () => {
    await makeMockEnv();
    onRpc(({ model, method, kwargs }) => {
        expect.step(`${model}:${method}:${kwargs.domain[0][2]}`);
    });

    const displayNames = await getService("name").loadDisplayNames("dev", [3]);
    expect(displayNames).toEqual({ 3: ERROR_INACCESSIBLE_OR_MISSING });
    expect.verifySteps(["dev:web_search_read:3"]);
});

test("batch + inaccessible/missing", async () => {
    await makeMockEnv();
    onRpc(({ model, method, kwargs }) => {
        expect.step(`${model}:${method}:${kwargs.domain[0][2]}`);
    });

    const loadPromise1 = getService("name").loadDisplayNames("dev", [1, 3]);
    expect.verifySteps([]);
    const loadPromise2 = getService("name").loadDisplayNames("dev", [2, 4]);
    expect.verifySteps([]);

    const [displayNames1, displayNames2] = await Promise.all([loadPromise1, loadPromise2]);
    expect(displayNames1).toEqual({ 1: "Julien", 3: ERROR_INACCESSIBLE_OR_MISSING });
    expect(displayNames2).toEqual({ 2: "Pierre", 4: ERROR_INACCESSIBLE_OR_MISSING });
    expect.verifySteps(["dev:web_search_read:1,3,2,4"]);
});
