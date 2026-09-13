// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { Deferred } from "@web/core/utils/concurrency";
import {
    registerServiceWorker,
    serviceWorkerService,
    watchServiceWorkerUpdates,
} from "@web/webclient/service_worker_service";

async function hasSettled(/** @type {Promise<any>} */ promise) {
    let settled = false;
    promise.then(
        () => (settled = true),
        () => (settled = true),
    );
    for (let i = 0; i < 5; i++) {
        await Promise.resolve();
    }
    return settled;
}

describe("service worker activation settlement", () => {
    test("helper sanity: hasSettled reports a resolved deferred", async () => {
        const resolved = new Deferred();
        resolved.resolve();
        expect(await hasSettled(resolved)).toBe(true);
        expect(await hasSettled(new Deferred())).toBe(false);
    });

    test("registerServiceWorker settles the deferred when SW is unavailable", async () => {
        const deferred = new Deferred();

        await registerServiceWorker(deferred);

        expect(await hasSettled(deferred)).toBe(true);
    });

    test("a consumer awaiting the deferred proceeds instead of hanging", async () => {
        const deferred = new Deferred();
        await registerServiceWorker(deferred);

        let reachedPastAwait = false;
        await deferred.then(() => {
            reachedPastAwait = true;
        });
        expect(reachedPastAwait).toBe(true);
    });

    test("the service exposes a `registrationSettled` promise that settles", async () => {
        const { registrationSettled } = serviceWorkerService.start();
        expect(await hasSettled(registrationSettled)).toBe(true);
    });

    test("the promise is named for what it guarantees, not for activation", async () => {
        const settled = new Deferred();
        await registerServiceWorker(settled);
        expect(await hasSettled(settled)).toBe(true);
        expect(Object.keys(serviceWorkerService.start())).toEqual([
            "controller",
            "registrationSettled",
            "stopWatching",
        ]);
    });
});

describe("service worker teardown", () => {
    test("destroy() stops the update watcher installed at registration", async () => {
        let stopped = 0;
        const registration = /** @type {any} */ ({
            waiting: null,
            installing: null,
            active: { state: "activated" },
            addEventListener() {},
            removeEventListener() {},
            update: async () => {},
        });
        patchWithCleanup(browser.navigator, {
            serviceWorker: /** @type {any} */ ({
                ready: Promise.resolve(),
                controller: {},
                register: async () => registration,
                addEventListener() {},
                removeEventListener() {},
            }),
        });
        patchWithCleanup(browser, {
            setInterval: () => 1,
            clearInterval: () => stopped++,
        });

        const service = serviceWorkerService.start();
        for (let i = 0; i < 50 && service.stopWatching === null; i++) {
            await Promise.resolve();
        }
        expect(service.stopWatching).not.toBe(null);

        service.destroy();
        expect(stopped).toBe(1);
    });

    test("destroy() before registration answers never starts a watcher", async () => {
        let stopped = 0;
        const registration = /** @type {any} */ ({
            waiting: null,
            installing: null,
            active: { state: "activated" },
            addEventListener() {},
            removeEventListener() {},
            update: async () => {},
        });
        patchWithCleanup(browser.navigator, {
            serviceWorker: /** @type {any} */ ({
                ready: Promise.resolve(),
                controller: {},
                register: async () => registration,
                addEventListener() {},
                removeEventListener() {},
            }),
        });
        patchWithCleanup(browser, {
            setInterval: () => 1,
            clearInterval: () => stopped++,
        });

        const service = serviceWorkerService.start();
        service.destroy();
        await service.registrationSettled;
        for (let i = 0; i < 5; i++) {
            await Promise.resolve();
        }

        expect(stopped).toBe(0);
    });
});

test("already-installing workers are watched, and stop removes worker listeners", () => {
    const worker = Object.assign(new EventTarget(), {
        state: "installing",
        postMessage: () => expect.step("promote"),
    });
    const registration = Object.assign(new EventTarget(), {
        active: {},
        waiting: null,
        installing: worker,
        update: async () => {},
    });
    const stop = watchServiceWorkerUpdates(/** @type {any} */ (registration));
    worker.state = "installed";
    worker.dispatchEvent(new Event("statechange"));
    expect.verifySteps(["promote"]);
    stop();
    worker.dispatchEvent(new Event("statechange"));
    expect.verifySteps([]);
});

for (const phase of ["registration", "readiness"]) {
    test(`destroy during pending ${phase} releases resources immediately`, async () => {
        const log = makeLogger("web.service_worker.test");
        const registered = new Deferred();
        const ready = new Deferred();
        let watching = 0;
        const worker = Object.assign(new EventTarget(), {
            state: "installing",
            postMessage: () => expect.step("promote"),
        });
        const registration = Object.assign(new EventTarget(), {
            active: {},
            waiting: null,
            installing: worker,
            update: async () => {},
        });
        patchWithCleanup(browser.navigator, {
            serviceWorker: /** @type {any} */ ({
                register: () => registered,
                ready,
                controller: {},
            }),
        });
        patchWithCleanup(browser, {
            setInterval: () => {
                watching++;
                return 1;
            },
            clearInterval: () => {
                watching--;
            },
        });
        const service = serviceWorkerService.start();
        if (phase === "readiness") {
            registered.resolve(registration);
            await hasSettled(service.registrationSettled);
            expect(watching).toBe(1);
        }
        service.destroy();
        log.lifecycle("destroyed", { phase, watching });
        expect(watching).toBe(0);
        expect(await hasSettled(service.registrationSettled)).toBe(true);
        registered.resolve(registration);
        ready.resolve(registration);
        await hasSettled(service.registrationSettled);
        worker.state = "installed";
        worker.dispatchEvent(new Event("statechange"));
        expect.verifySteps([]);
        expect(watching).toBe(0);
    });
}
