/** @odoo-module **/

import { makeEnv, startServices } from "@web/env";
import { registry } from "@web/core/registry";
import {
    clearRegistryWithCleanup,
    clearServicesMetadataWithCleanup,
    makeTestEnv,
} from "./helpers/mock_env";
import { makeDeferred, nextTick, patchWithCleanup } from "./helpers/utils";

const serviceRegistry = registry.category("services");

QUnit.module("env");

QUnit.test("can start a service", async (assert) => {
    serviceRegistry.add("test", {
        start() {
            return 17;
        },
    });
    const env = await makeTestEnv();
    assert.strictEqual(env.services.test, 17);
});

QUnit.test("properly handle crash in service start", async (assert) => {
    patchWithCleanup(console, {
        error: () => assert.step("log"),
    });
    serviceRegistry.add("test", {
        start() {
            return 17;
        },
    });
    serviceRegistry.add("ouch", {
        start() {
            throw new Error("boom");
        },
    });
    const env = await makeTestEnv();
    assert.strictEqual(env.services.test, 17);
    assert.ok(env.services.ouch instanceof Error);
    assert.verifySteps(["log"]);
});

QUnit.test("properly handle crash in async service start", async (assert) => {
    patchWithCleanup(console, {
        error: () => assert.step("log"),
    });
    serviceRegistry.add("test", {
        start() {
            return 17;
        },
    });
    serviceRegistry.add("ouch", {
        async start() {
            throw new Error("boom");
        },
    });
    const env = await makeTestEnv();
    assert.strictEqual(env.services.test, 17);
    assert.ok(env.services.ouch instanceof Error);
    assert.verifySteps(["log"]);
});

QUnit.test("can start an asynchronous service", async (assert) => {
    const def = makeDeferred();
    serviceRegistry.add("test", {
        async start() {
            assert.step("before");
            const result = await def;
            assert.step("after");
            return result;
        },
    });
    const prom = makeTestEnv();
    await Promise.resolve(); // Wait for startServices
    assert.verifySteps(["before"]);
    def.resolve(15);
    const env = await prom;
    assert.verifySteps(["after"]);
    assert.strictEqual(env.services.test, 15);
});

QUnit.test("can start two sequentially dependant asynchronous services", async (assert) => {
    const def1 = makeDeferred();
    const def2 = makeDeferred();
    serviceRegistry.add("test2", {
        dependencies: ["test1"],
        start() {
            assert.step("test2");
            return def2;
        },
    });
    serviceRegistry.add("test1", {
        start() {
            assert.step("test1");
            return def1;
        },
    });
    serviceRegistry.add("test3", {
        dependencies: ["test2"],
        start() {
            assert.step("test3");
        },
    });
    const promise = makeTestEnv();
    await nextTick();
    assert.verifySteps(["test1"]);
    def2.resolve();
    await nextTick();
    assert.verifySteps([]);
    def1.resolve();
    await nextTick();
    assert.verifySteps(["test2", "test3"]);
    await promise;
});

QUnit.test("can start two independant asynchronous services in parallel", async (assert) => {
    const def1 = makeDeferred();
    const def2 = makeDeferred();
    serviceRegistry.add("test1", {
        start() {
            assert.step("test1");
            return def1;
        },
    });
    serviceRegistry.add("test2", {
        start() {
            assert.step("test2");
            return def2;
        },
    });
    serviceRegistry.add("test3", {
        dependencies: ["test1", "test2"],
        start() {
            assert.step("test3");
        },
    });
    const promise = makeTestEnv();
    await nextTick();
    assert.verifySteps(["test1", "test2"]);
    def1.resolve();
    await nextTick();
    assert.verifySteps([]);
    def2.resolve();
    await nextTick();
    assert.verifySteps(["test3"]);
    await promise;
});

QUnit.test("can start a service with a dependency", async (assert) => {
    serviceRegistry.add("aang", {
        dependencies: ["appa"],
        start() {
            assert.step("aang");
        },
    });
    serviceRegistry.add("appa", {
        start() {
            assert.step("appa");
        },
    });
    await makeTestEnv();
    assert.verifySteps(["appa", "aang"]);
});

QUnit.test("get an object containing dependencies as second arg", async (assert) => {
    serviceRegistry.add("aang", {
        dependencies: ["appa"],
        start(env, deps) {
            assert.deepEqual(deps, { appa: "flying bison" });
        },
    });
    serviceRegistry.add("appa", {
        start() {
            return "flying bison";
        },
    });
    await makeTestEnv();
});

QUnit.test(
    "startServices: throws if all dependencies are not met in the same microtick as the call",
    async function (assert) {
        assert.expect(3);
        clearRegistryWithCleanup(serviceRegistry);
        clearServicesMetadataWithCleanup();

        const serviceA = {
            start() {
                return "a";
            },
        };
        const serviceB = {
            dependencies: ["a"],
            start() {
                return "b";
            },
        };
        const env = makeEnv();

        serviceRegistry.add("b", serviceB);
        const prom = startServices(env);
        await Promise.resolve();
        assert.rejects(prom, "Some services could not be started: b. Missing dependencies: a");
        assert.deepEqual(env.services, {});

        serviceRegistry.add("a", serviceA);
        await startServices(env);
        assert.deepEqual(env.services, { a: "a", b: "b" });
    }
);

QUnit.test(
    "startServices: waits for all synchronous code before attempting to start services",
    async function (assert) {
        assert.expect(1);
        clearRegistryWithCleanup(serviceRegistry);
        clearServicesMetadataWithCleanup();

        const serviceA = {
            start() {
                return "a";
            },
        };
        const serviceB = {
            dependencies: ["a"],
            start() {
                return "b";
            },
        };

        const env = makeEnv();
        serviceRegistry.add("b", serviceB);
        const prom = startServices(env);
        // Dependency added in the same microtick doesn't cause startServices to throw even if it was added after the call
        // (eg, a module is defined after main.js)
        serviceRegistry.add("a", serviceA);

        await prom;
        assert.deepEqual(env.services, { a: "a", b: "b" });
    }
);
