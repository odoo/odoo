/** @odoo-module */

import { whenReady } from "@odoo/owl";
import { isInDOM, mockedMatchMedia } from "@web/../lib/hoot-dom/helpers/dom";
import { MockMath } from "./math";
import { mockNavigator } from "./navigator";
import {
    MockHistory,
    MockRequest,
    MockResponse,
    MockSharedWorker,
    MockWebSocket,
    MockWorker,
    MockXMLHttpRequest,
    mockedFetch,
} from "./network";
import { MockNotification } from "./notification";
import { MockStorage } from "./storage";
import {
    MockDate,
    mockedCancelAnimationFrame,
    mockedClearInterval,
    mockedClearTimeout,
    mockedRequestAnimationFrame,
    mockedSetInterval,
    mockedSetTimeout,
} from "./time";
import { createMock } from "../hoot_utils";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Object, document } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {any} target
 * @param {Record<string, PropertyDescriptor>} descriptors
 */
const applyPropertyDescriptors = (target, descriptors) => {
    for (const [property, rawDescriptor] of Object.entries(descriptors)) {
        const owner = findPropertyOwner(target, property);
        originalDescriptors.push({
            descriptor: Object.getOwnPropertyDescriptor(owner, property),
            owner,
            property,
            target,
        });
        const descriptor = { ...rawDescriptor };
        if ("value" in descriptor) {
            descriptor.writable = false;
        }
        Object.defineProperty(owner, property, descriptor);
    }
};

/**
 * @template T
 * @param {T} target
 * @param {keyof T} property
 */
const findOriginalDescriptor = (target, property) => {
    for (const { descriptor, target: t, property: p } of originalDescriptors) {
        if (t === target && p === property) {
            return descriptor;
        }
    }
    return null;
};

/**
 * @param {unknown} object
 * @param {string} property
 * @returns {any}
 */
const findPropertyOwner = (object, property) => {
    if (Object.hasOwn(object, property)) {
        return object;
    }
    const prototype = Object.getPrototypeOf(object);
    if (prototype) {
        return findPropertyOwner(prototype, property);
    }
    return object;
};

/**
 * @param {EventTarget} target
 */
const mockEventListeners = (target) => {
    const { addEventListener, removeEventListener } = target;

    /** @type {addEventListener} */
    const mockedAddEventListener = (type, callback, options) => {
        const listeners = listenerMap.get(target);
        if (listeners) {
            if (options?.once) {
                const originalCallback = callback;
                callback = (...args) => {
                    unregisterListener(listeners, type, callback);
                    return originalCallback(...args);
                };
            }
            registerListener(listeners, type, callback);
        }
        return addEventListener.call(target, type, callback, options);
    };

    /** @type {removeEventListener} */
    const mockedRemoveEventListener = (type, callback, options) => {
        const listeners = listenerMap.get(target);
        if (listeners) {
            unregisterListener(listeners, type, callback);
        }
        return removeEventListener.call(target, type, callback, options);
    };

    target.addEventListener = mockedAddEventListener;
    target.removeEventListener = mockedRemoveEventListener;
};

/**
 * @param {EventTarget} target
 * @param {string} type
 * @param {EventListener} callback
 */
const registerListener = (listeners, type, callback) => {
    if (!listeners[type]) {
        listeners[type] = new Set();
    }
    listeners[type].add(callback);
};

/**
 * @param {EventTarget} target
 * @param {string} type
 * @param {EventListener} callback
 */
const unregisterListener = (listeners, type, callback) => {
    if (!listeners[type]) {
        return;
    }
    listeners[type].delete(callback);
    if (!listeners[type].size) {
        delete listeners[type];
    }
};

/** @type {{ descriptor: PropertyDescriptor; owner: any; property: string; target: any }[]} */
const originalDescriptors = [];
const listenerMap = new Map();

const mockHistory = new MockHistory();
const mockLocalStorage = new MockStorage();
// const mockLocation = new MockLocation(); // TODO: does not work
const mockSessionStorage = new MockStorage();
let mockTitle = "";

// Mock descriptors
const DOCUMENT_MOCK_DESCRIPTORS = {
    title: {
        get: () => mockTitle,
        set: (value) => (mockTitle = value),
    },
};
const WINDOW_MOCK_DESCRIPTORS = {
    Date: { value: MockDate },
    Math: { value: MockMath },
    Notification: { value: MockNotification },
    Request: { value: MockRequest },
    Response: { value: MockResponse },
    SharedWorker: { value: MockSharedWorker },
    WebSocket: { value: MockWebSocket },
    Worker: { value: MockWorker },
    XMLHttpRequest: { value: MockXMLHttpRequest },
    cancelAnimationFrame: { value: mockedCancelAnimationFrame },
    clearInterval: { value: mockedClearInterval },
    clearTimeout: { value: mockedClearTimeout },
    fetch: { value: mockedFetch },
    history: { value: mockHistory },
    localStorage: { value: mockLocalStorage },
    // location: { value: mockLocation }, // TODO: does not work
    matchMedia: { value: mockedMatchMedia },
    navigator: { value: mockNavigator },
    requestAnimationFrame: { value: mockedRequestAnimationFrame },
    sessionStorage: { value: mockSessionStorage },
    setInterval: { value: mockedSetInterval },
    setTimeout: { value: mockedSetTimeout },
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupWindow() {
    // Listeners
    for (const [target, listeners] of listenerMap) {
        if (!isInDOM(target)) {
            continue;
        }
        for (const [type, callbacks] of Object.entries(listeners)) {
            for (const callback of callbacks) {
                target.removeEventListener(type, callback);
            }
        }
    }
}

export function getTitle() {
    const titleDescriptor = findOriginalDescriptor(document, "title");
    if (titleDescriptor) {
        return titleDescriptor.get.call(document);
    } else {
        return document.title;
    }
}

/**
 * @param {typeof globalThis} global
 */
export function patchWindow({ document, window } = globalThis) {
    applyPropertyDescriptors(window, WINDOW_MOCK_DESCRIPTORS);
    mockEventListeners(window);
    whenReady(() => {
        applyPropertyDescriptors(document, DOCUMENT_MOCK_DESCRIPTORS);
        for (const target of [document, document.body, document.head]) {
            mockEventListeners(target);
        }
    });
}

/**
 * @param {string} value
 */
export function setTitle(value) {
    const titleDescriptor = findOriginalDescriptor(document, "title");
    if (titleDescriptor) {
        titleDescriptor.set.call(document, value);
    } else {
        document.title = value;
    }
}

/**
 * TODO: is this useful?
 */
export function unpatchWindow() {
    for (const { descriptor, owner, property } of originalDescriptors) {
        Object.defineProperty(owner, property, descriptor);
    }
    originalDescriptors.length = 0;
}

/**
 * Returns a function checking that no listeners are left on the given target, and
 * optionally removing them.
 *
 * @param {...EventTarget} targets
 */
export function watchListeners(...targets) {
    for (const target of targets) {
        listenerMap.set(target, {});
    }

    return function unwatchListeners() {
        listenerMap.clear();
    };
}
