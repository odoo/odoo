/** @odoo-module **/

import { makeEnv, mountComponent, startServices } from "@web/env";
import { registry } from "@web/core/registry";
import {
    clearRegistryWithCleanup,
    clearServicesMetadataWithCleanup,
    makeTestEnv,
} from "./helpers/mock_env";
import { getFixture, makeDeferred, nextTick, patchWithCleanup } from "./helpers/utils";
import { Component, xml } from "@odoo/owl";
import { registerCleanup } from "@web/../tests/helpers/cleanup";

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
        await assert.rejects(
            prom,
            "Some services could not be started: b. Missing dependencies: a"
        );
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

QUnit.test(
    "mountComponent creates an env and sets the application as root when no env is provided",
    async function (assert) {
        clearRegistryWithCleanup(serviceRegistry);
        clearServicesMetadataWithCleanup();

        const myService = {
            start() {
                return "a";
            },
        };
        serviceRegistry.add("my_service", myService);

        class Root extends Component {
            static template = xml`Root`;
        }
        const app = await mountComponent(Root, getFixture());
        registerCleanup(() => {
            delete odoo.__WOWL_DEBUG__;
        });
        const { env } = app;

        assert.deepEqual(env.services, { my_service: "a" });
        assert.deepEqual(odoo.__WOWL_DEBUG__, { root: app.root.component });
        assert.strictEqual(getFixture().textContent, "Root");
    }
);

QUnit.test(
    "mountComponent uses the env when provided and doesn't start the services",
    async function (assert) {
        clearRegistryWithCleanup(serviceRegistry);
        clearServicesMetadataWithCleanup();

        const myService = {
            start() {
                assert.step("starting myService");
                return "a";
            },
        };
        serviceRegistry.add("my_service", myService);
        const env = makeEnv();
        assert.verifySteps([]);
        await startServices(env);
        assert.verifySteps(["starting myService"]);

        class Root extends Component {
            static template = xml`Root`;
        }

        const app = await mountComponent(Root, getFixture(), { env });
        assert.verifySteps([]);
        assert.strictEqual(app.env.services, env.services);
        assert.strictEqual(odoo.__WOWL_DEBUG__, undefined);
        assert.strictEqual(getFixture().textContent, "Root");
    }
);

QUnit.test("mountComponent: can pass props to the root component", async function (assert) {
    clearRegistryWithCleanup(serviceRegistry);
    clearServicesMetadataWithCleanup();

    class Root extends Component {
        static template = xml`<t t-esc="props.text"/>`;
    }

    await mountComponent(Root, getFixture(), { props: { text: "text from props" } });
    registerCleanup(() => {
        delete odoo.__WOWL_DEBUG__;
    });

    assert.strictEqual(getFixture().textContent, "text from props");
});
