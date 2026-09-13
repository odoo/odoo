// @ts-check
/** @odoo-module native */

import {
    onWillDestroy,
    onWillStart,
    onWillUpdateProps,
    reactive,
    toRaw,
    useComponent,
    useState,
} from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { deepEqual } from "@web/core/utils/collections/objects";
import { useService } from "@web/core/utils/hooks";

const log = makeLogger("web.field.special_data");

/** @import { Component } from "@odoo/owl" */

/** @type {WeakMap<Map<string, Promise<any>>, Map<string, Set<() => void>>>} */
const staleReloadSubscribers = new WeakMap();

/**
 * @param {Map<string, Promise<any>>} specialDataCaches
 * @param {string} key
 * @returns {Set<() => void>}
 */
function subscribersFor(specialDataCaches, key) {
    let byKey = staleReloadSubscribers.get(specialDataCaches);
    if (!byKey) {
        byKey = new Map();
        staleReloadSubscribers.set(specialDataCaches, byKey);
    }
    let subscribers = byKey.get(key);
    if (!subscribers) {
        subscribers = new Set();
        byKey.set(key, subscribers);
    }
    return subscribers;
}

/**
 * @param {Map<string, Promise<any>>} cache
 * @param {() => void} subscriber
 */
function cacheSubscriptions(cache, subscriber) {
    const keys = new Set();
    return {
        add(key) {
            subscribersFor(cache, key).add(subscriber);
            keys.add(key);
        },
        clear() {
            const byKey = staleReloadSubscribers.get(cache);
            for (const key of keys) {
                const subscribers = byKey.get(key);
                subscribers.delete(subscriber);
                if (!subscribers.size) {
                    byKey.delete(key);
                }
            }
            keys.clear();
        },
    };
}

/**
 * @param {import("@web/core/network/orm_service").ORM} orm
 * @param {Map<string, Promise<any>>} specialDataCaches
 * @param {string} key
 * @param {Parameters<import("@web/core/network/orm_service").ORM["call"]>} args
 */
function cachedCall(orm, specialDataCaches, key, args) {
    if (!specialDataCaches.has(key)) {
        /** @type {(value: any) => void} */
        let deliver;
        const delivered = new Promise((resolve) => {
            deliver = resolve;
        });
        const prom = orm
            .cache({
                type: "disk",
                update: "always",
                callback: (res, hasChanged) => {
                    deliver(res);
                    specialDataCaches.set(key, Promise.resolve(res));
                    if (!hasChanged) {
                        return;
                    }
                    for (const subscriber of [
                        ...(staleReloadSubscribers.get(specialDataCaches)?.get(key) ||
                            []),
                    ]) {
                        subscriber();
                    }
                },
            })
            .call(...args);
        const settled = Promise.race([prom, delivered]);
        specialDataCaches.set(key, settled);
        prom.catch(() => {
            if (specialDataCaches.get(key) === settled) {
                specialDataCaches.delete(key);
            }
        });
    }
    return specialDataCaches.get(key);
}

/**
 * @template T, [Props=any]
 * @param {(orm: import("@web/core/network/orm_service").ORM, props: Component<Props>["props"]) => Promise<T>} loadFn
 * @returns {{ data: T, isReady: boolean }}
 */
export function useSpecialData(loadFn) {
    const component = useComponent();
    const record = component.props.record;
    const specialDataCaches = toRaw(record.model.specialDataCaches);
    const orm = useService("orm");
    let loadTicket = 0;
    let destroyed = false;
    let currentProps = component.props;
    let reloadQueued = false;
    let currentLoad;
    const subscriptions = cacheSubscriptions(specialDataCaches, scheduleReload);
    function requestLoad(props) {
        return (currentLoad = load(props));
    }
    function scheduleReload() {
        if (destroyed || reloadQueued) {
            return;
        }
        // Invalidate immediately, before an older response can settle. Batch the
        // reads so one record update does not load once per changed dependency.
        ++loadTicket;
        result.isReady = false;
        reloadQueued = true;
        Promise.resolve().then(() => {
            reloadQueued = false;
            if (!destroyed) {
                return requestLoad(currentProps);
            }
        });
    }
    onWillDestroy(() => {
        destroyed = true;
        ++loadTicket;
        subscriptions.clear();
    });

    /** @type {{ data: T, isReady: boolean }} */
    const result = useState(/** @type {any} */ ({ data: {}, isReady: false }));
    async function load(nextProps) {
        currentProps = nextProps;
        const ticket = ++loadTicket;
        subscriptions.clear();
        result.isReady = false;
        const props = { ...nextProps };
        if (props.record) {
            props.record = reactive(props.record, scheduleReload);
        }
        const ormWithCache = Object.create(orm);
        ormWithCache.call = (/** @type {Parameters<typeof orm.call>} */ ...args) => {
            const key = JSON.stringify(args);
            if (!destroyed && ticket === loadTicket) {
                subscriptions.add(key);
            }
            return cachedCall(orm, specialDataCaches, key, args);
        };
        log.pipeline("load", { ticket, field: props.name });
        try {
            const data = await loadFn(ormWithCache, props);
            if (destroyed || ticket !== loadTicket) {
                log.pipeline("superseded", { ticket });
                return;
            }
            if (!deepEqual(toRaw(result.data), data)) {
                result.data = data;
            }
            result.isReady = true;
            log.pipeline("ready", { ticket });
        } catch (error) {
            log.pipeline("failed", { ticket });
            throw error;
        }
    }
    onWillStart(async () => {
        await requestLoad(component.props);
        // Superseding the initial request must not release the first render
        // while data still has its uninitialized shape.
        while (!destroyed && !result.isReady) {
            await currentLoad;
        }
    });
    // Do not hold Owl's render on a replacement request: consumers must be
    // able to render their disabled state while retaining the previous label.
    onWillUpdateProps((props) => {
        void requestLoad(props);
    });
    return result;
}
