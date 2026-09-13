// @ts-check
/** @odoo-module native */

import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { RpcEvent } from "@web/core/events";
import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";

const log = makeLogger("web.service_worker");

const SERVICE_WORKER_UPDATE_INTERVAL = 6 * 60 * 60 * 1000;

const SERVICE_WORKER_READY_TIMEOUT = 20 * 1000;

/**
 * @param {ServiceWorkerRegistration} registration
 * @returns {() => void}
 */
export function watchServiceWorkerUpdates(registration) {
    /** @type {Map<ServiceWorker, () => void>} */
    const workerListeners = new Map();
    /** @param {ServiceWorker | null} worker */
    const promoteWhenInstalled = (worker) => {
        if (!worker || workerListeners.has(worker)) {
            return;
        }
        const promote = () => {
            if (worker.state === "installed" && registration.active) {
                worker.postMessage({ type: "SKIP_WAITING" });
            }
        };
        workerListeners.set(worker, promote);
        worker.addEventListener("statechange", promote);
        promote();
    };
    promoteWhenInstalled(registration.waiting);
    promoteWhenInstalled(registration.installing);
    const onUpdateFound = () => promoteWhenInstalled(registration.installing);
    registration.addEventListener("updatefound", onUpdateFound);
    const checkForUpdate = () => registration.update().catch(() => {});
    const intervalId = browser.setInterval(
        checkForUpdate,
        SERVICE_WORKER_UPDATE_INTERVAL,
    );
    const onVisibilityChange = () => {
        if (document.visibilityState === "visible") {
            checkForUpdate();
        }
    };
    browser.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
        for (const [worker, listener] of workerListeners) {
            worker.removeEventListener("statechange", listener);
        }
        workerListeners.clear();
        browser.clearInterval(intervalId);
        registration.removeEventListener("updatefound", onUpdateFound);
        browser.removeEventListener("visibilitychange", onVisibilityChange);
    };
}

/**
 * @param {Deferred} settledDeferred
 * @param {AbortSignal} [signal]
 * @returns {Promise<{
 *   registration: ServiceWorkerRegistration | undefined,
 *   stopWatching: () => void,
 * }>}
 */
export async function registerServiceWorker(settledDeferred, signal) {
    const { serviceWorker } = browser.navigator;
    let readyTimeoutId;
    /** @type {() => void} */
    let stopWatching = () => {};
    /** @type {ServiceWorkerRegistration | undefined} */
    let registration;
    const aborted = new Deferred();
    const onAbort = () => {
        stopWatching();
        stopWatching = () => {};
        aborted.resolve();
        log.lifecycle("registration cancelled");
    };
    signal?.addEventListener("abort", onAbort, { once: true });
    try {
        if (serviceWorker && !signal?.aborted) {
            registration = await Promise.race([
                serviceWorker.register("/web/service-worker.js", { scope: "/odoo" }),
                aborted.then(() => undefined),
            ]);
            if (!registration || signal?.aborted) {
                return { registration, stopWatching };
            }
            stopWatching = watchServiceWorkerUpdates(registration);
            log.lifecycle("watching updates");
            await Promise.race([
                serviceWorker.ready,
                aborted,
                new Promise((resolve) => {
                    readyTimeoutId = browser.setTimeout(
                        resolve,
                        SERVICE_WORKER_READY_TIMEOUT,
                    );
                }),
            ]);
            if (!signal?.aborted && !serviceWorker.controller) {
                rpcBus.trigger(RpcEvent.CLEAR_CACHES);
            }
        }
    } catch (error) {
        console.error("Service worker registration failed, error:", error);
    } finally {
        signal?.removeEventListener("abort", onAbort);
        browser.clearTimeout(readyTimeoutId);
        settledDeferred.resolve();
    }
    return { registration, stopWatching };
}

class ServiceWorkerService {
    constructor() {
        this.controller = new AbortController();
        /** @type {Promise<void> & { resolve: (value?: any) => void, reject: (reason?: any) => void }} */
        const settledDeferred = new Deferred();
        /** @type {Promise<void>} */
        this.registrationSettled = settledDeferred;
        /** @type {(() => void) | null} */
        this.stopWatching = null;
        registerServiceWorker(settledDeferred, this.controller.signal).then(
            ({ stopWatching }) => {
                if (this.stopWatching === null) {
                    this.stopWatching = stopWatching;
                } else {
                    stopWatching();
                }
            },
        );
    }

    destroy() {
        this.controller.abort();
        this.stopWatching?.();
        this.stopWatching = () => {};
    }
}

export const serviceWorkerService = {
    /** @returns {ServiceWorkerService} */
    start() {
        return new ServiceWorkerService();
    },
};

registry.category("services").add("service_worker", serviceWorkerService);
