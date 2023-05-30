/** @odoo-module **/

import { ERROR_INACCESSIBLE_OR_MISSING, nameService } from "@web/core/name_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

let serverData;
QUnit.module("Name Service", {
    async beforeEach() {
        serverData = {
            models: {
                dev: {
                    fields: {},
                    records: [
                        { id: 1, display_name: "Julien" },
                        { id: 2, display_name: "Pierre" },
                    ],
                },
            },
        };
        serviceRegistry.add("name", nameService);
    },
});

QUnit.test("single loadDisplayNames", async (assert) => {
    const env = await makeTestEnv({ serverData });
    const displayNames = await env.services.name.loadDisplayNames("dev", [1, 2]);
    assert.deepEqual(displayNames, { 1: "Julien", 2: "Pierre" });
});

QUnit.test("loadDisplayNames is done in silent mode", async (assert) => {
    assert.expect(2);
    const env = await makeTestEnv({ serverData });
    env.bus.addEventListener("RPC:REQUEST", (ev) => {
        const silent = ev.detail.settings.silent;
        assert.step("RPC:REQUEST" + (silent ? " (silent)" : ""));
    });
    await env.services.name.loadDisplayNames("dev", [1]);
    assert.verifySteps(["RPC:REQUEST (silent)"]);
});

QUnit.test("single loadDisplayNames following addDisplayNames", async (assert) => {
    const mockRPC = (_, { method }) => {
        assert.step(method);
    };
    const env = await makeTestEnv({ serverData, mockRPC });
    env.services.name.addDisplayNames("dev", { 1: "JUM", 2: "PIPU" });
    const displayNames = await env.services.name.loadDisplayNames("dev", [1, 2]);
    assert.deepEqual(displayNames, { 1: "JUM", 2: "PIPU" });
    assert.verifySteps([]);
});

QUnit.test("single loadDisplayNames following addDisplayNames (2)", async (assert) => {
    const mockRPC = (_, { kwargs, method }) => {
        assert.step(method);
        const ids = kwargs.domain[0][2];
        assert.step(`id(s): ${ids.join(", ")}`);
    };
    const env = await makeTestEnv({ serverData, mockRPC });
    env.services.name.addDisplayNames("dev", { 1: "JUM" });
    const displayNames = await env.services.name.loadDisplayNames("dev", [1, 2]);
    assert.deepEqual(displayNames, { 1: "JUM", 2: "Pierre" });
    assert.verifySteps(["web_search_read", "id(s): 2"]);
});

QUnit.test("loadDisplayNames in batch", async (assert) => {
    const mockRPC = (_, { kwargs, method }) => {
        assert.step(method);
        const ids = kwargs.domain[0][2];
        assert.step(`id(s): ${ids.join(", ")}`);
    };
    const env = await makeTestEnv({ serverData, mockRPC });
    const prom1 = env.services.name.loadDisplayNames("dev", [1]);
    assert.verifySteps([]);
    const prom2 = env.services.name.loadDisplayNames("dev", [2]);
    assert.verifySteps([]);
    const [displayNames1, displayNames2] = await Promise.all([prom1, prom2]);
    assert.deepEqual(displayNames1, { 1: "Julien" });
    assert.deepEqual(displayNames2, { 2: "Pierre" });
    assert.verifySteps(["web_search_read", "id(s): 1, 2"]);
});

QUnit.test("loadDisplayNames on different models", async (assert) => {
    serverData.models.PO = {
        fields: {},
        records: [{ id: 1, display_name: "Damien" }],
    };
    const mockRPC = (_, { kwargs, method, model }) => {
        assert.step(method);
        assert.step(model);
        const ids = kwargs.domain[0][2];
        assert.step(`id(s): ${ids.join(", ")}`);
    };
    const env = await makeTestEnv({ serverData, mockRPC });
    const prom1 = env.services.name.loadDisplayNames("dev", [1]);
    assert.verifySteps([]);
    const prom2 = env.services.name.loadDisplayNames("PO", [1]);
    assert.verifySteps([]);
    const [displayNames1, displayNames2] = await Promise.all([prom1, prom2]);
    assert.deepEqual(displayNames1, { 1: "Julien" });
    assert.deepEqual(displayNames2, { 1: "Damien" });
    assert.verifySteps(["web_search_read", "dev", "id(s): 1", "web_search_read", "PO", "id(s): 1"]);
});

QUnit.test("invalid id", async (assert) => {
    assert.expect(1);
    const env = await makeTestEnv({ serverData });
    try {
        await env.services.name.loadDisplayNames("dev", ["a"]);
    } catch (e) {
        assert.strictEqual(e.message, "Invalid ID: a");
    }
});

QUnit.test("inaccessible or missing id", async (assert) => {
    const mockRPC = (_, { method }) => {
        assert.step(method);
    };
    const env = await makeTestEnv({ serverData, mockRPC });
    const displayNames = await env.services.name.loadDisplayNames("dev", [3]);
    assert.deepEqual(displayNames, { 3: ERROR_INACCESSIBLE_OR_MISSING });
    assert.verifySteps(["web_search_read"]);
});

QUnit.test("batch + inaccessible/missing", async (assert) => {
    const mockRPC = (_, { method, kwargs }) => {
        assert.step(method);
        const ids = kwargs.domain[0][2];
        assert.step(`id(s): ${ids.join(", ")}`);
    };
    const env = await makeTestEnv({ serverData, mockRPC });
    const prom1 = env.services.name.loadDisplayNames("dev", [1, 3]);
    assert.verifySteps([]);
    const prom2 = env.services.name.loadDisplayNames("dev", [2, 4]);
    assert.verifySteps([]);
    const [displayNames1, displayNames2] = await Promise.all([prom1, prom2]);
    assert.deepEqual(displayNames1, { 1: "Julien", 3: ERROR_INACCESSIBLE_OR_MISSING });
    assert.deepEqual(displayNames2, { 2: "Pierre", 4: ERROR_INACCESSIBLE_OR_MISSING });
    assert.verifySteps(["web_search_read", "id(s): 1, 3, 2, 4"]);
});
