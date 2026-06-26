import { afterEach, beforeEach, describe, expect, getFixture, test, tick } from "@odoo/hoot";
import { Component, signal, xml } from "@odoo/owl";
import {
    allowTranslations,
    clearRegistry,
    makeMockEnv,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { LegacyServiceStarterPlugin, startServices } from "@web/core/legacy_service_starter";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { makeEnv, mountComponent } from "@web/env";

describe.current.tags("headless");

const servicesRegistry = registry.category("services");

beforeEach(() => {
    clearRegistry(servicesRegistry);
    // ideally, should not be done like this, we should simply start odoo with
    // the services that we want. but for now, it will do
    patchWithCleanup(services, {
        _items: signal.Array([]),
    });
    services.add(LegacyServiceStarterPlugin);
});
afterEach(() => {
    delete odoo.isReady;
    delete odoo.__WOWL_DEBUG__;
});

/**
 * @param {string} name
 * @param {string[]} dependencies
 * @param {(env: import("@web/env").OdooEnv, dependencies: Record<string, any>) => any} factory
 */
function registerService(name, dependencies, factory) {
    servicesRegistry.add(name, {
        dependencies,
        start: factory,
    });
}

test(`can start a service`, async () => {
    registerService("test", [], () => 17);
    const env = await makeMockEnv();
    expect(env.services.test).toBe(17);
});

test(`crashing service start causes startService to crash`, async () => {
    registerService("ouch", [], () => {
        throw new Error("boom");
    });
    await expect(makeMockEnv()).rejects.toThrow("boom");
});

test(`crashing async service start causes startService to crash`, async () => {
    registerService("ouch", [], async () => {
        throw new Error("boom");
    });
    await expect(makeMockEnv()).rejects.toThrow("boom");
});

test(`can start an asynchronous service`, async () => {
    const deferred = Promise.withResolvers();
    registerService("test", [], async () => {
        expect.step("before");
        const result = await deferred.promise;
        expect.step("after");
        return result;
    });

    const envCreationPromise = makeMockEnv();
    await tick(); // wait for startServices
    expect.verifySteps(["before"]);

    deferred.resolve(15);
    const env = await envCreationPromise;
    expect.verifySteps(["after"]);
    expect(env.services.test).toBe(15);
});

test(`can start a service with a dependency`, async () => {
    registerService("aang", ["appa"], () => expect.step("aang"));
    registerService("appa", [], () => expect.step("appa"));

    await makeMockEnv();
    expect.verifySteps(["appa", "aang"]);
});

test(`get an object containing dependencies as second arg`, async () => {
    registerService("aang", ["appa"], (_, dependencies) => {
        expect.step("aang");
        expect(dependencies).toEqual({ appa: "flying bison" });
    });
    registerService("appa", [], () => {
        expect.step("appa");
        return "flying bison";
    });

    await makeMockEnv();
    expect.verifySteps(["appa", "aang"]);
});

test(`can start two sequentially dependant asynchronous services`, async () => {
    const deferred2 = Promise.withResolvers();
    registerService("test2", ["test1"], () => {
        expect.step("test2");
        return deferred2.promise;
    });

    const deferred1 = Promise.withResolvers();
    registerService("test1", [], () => {
        expect.step("test1");
        return deferred1.promise;
    });

    registerService("test3", ["test2"], () => {
        expect.step("test3");
    });

    const envCreationPromise = makeMockEnv();
    await tick();
    expect.verifySteps(["test1"]);

    deferred2.resolve();
    await tick();
    expect.verifySteps([]);

    deferred1.resolve();
    await tick();
    expect.verifySteps(["test2", "test3"]);

    await envCreationPromise;
});

test(`can start two independant asynchronous services in parallel`, async () => {
    const deferred1 = Promise.withResolvers();
    registerService("test1", [], () => {
        expect.step("test1");
        return deferred1.promise;
    });

    const deferred2 = Promise.withResolvers();
    registerService("test2", [], () => {
        expect.step("test2");
        return deferred2.promise;
    });

    registerService("test3", ["test1", "test2"], () => {
        expect.step("test3");
    });

    const envCreationPromise = makeMockEnv();
    await tick();
    expect.verifySteps(["test1", "test2"]);

    deferred1.resolve();
    await tick();
    expect.verifySteps([]);

    deferred2.resolve();
    await tick();
    expect.verifySteps(["test3"]);

    await envCreationPromise;
});

test(`startServices: throws if all dependencies are not met in the same microtick as the call`, async () => {
    const env = makeEnv();
    registerService("b", ["a"], () => "b");

    const serviceStartingPromise = startServices(env, (fn) => fn());
    await expect(serviceStartingPromise).rejects.toThrow(
        "Some services could not be started: b. Missing dependencies: a"
    );
    expect(env.services).toEqual({});

    registerService("a", [], () => "a");
    await startServices(env, (fn) => fn());
    expect(env.services).toEqual({ a: "a", b: "b" });
});

test(`startServices: waits for all synchronous code before attempting to start services`, async () => {
    const env = makeEnv();
    registerService("b", ["a"], () => "b");

    const serviceStartingPromise = startServices(env, (fn) => fn());
    // Dependency added in the same microtick doesn't cause startServices to throw even if it was added after the call
    // (eg, a module is defined after main.js)
    registerService("a", [], () => "a");

    await serviceStartingPromise;
    expect(env.services).toEqual({ a: "a", b: "b" });
});

test(`mountComponent creates an env and sets the application as root`, async () => {
    allowTranslations();
    registerService("my_service", [], () => "a");

    class Root extends Component {
        static template = xml`Root`;
        static props = ["*"];
    }
    const { app, env } = await mountComponent(Root, getFixture());
    expect(env.services).toEqual({ my_service: "a" });
    const [firstRoot] = app.roots;
    expect(odoo.__WOWL_DEBUG__).toEqual({ root: firstRoot.node.component });
    expect(getFixture()).toHaveText("Root");
});

test(`mountComponent: can pass props to the root component`, async () => {
    class Root extends Component {
        static template = xml`<t t-out="this.props.text"/>`;
        static props = ["*"];
    }

    await mountComponent(Root, getFixture(), { props: { text: "text from props" } });
    expect(getFixture()).toHaveText("text from props");
});
