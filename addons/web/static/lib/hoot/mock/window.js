/** @odoo-module */

import { EventBus, whenReady } from "@odoo/owl";
import { getCurrentDimensions, mockedMatchMedia } from "@web/../lib/hoot-dom/helpers/dom";
import { getRunner } from "../main_runner";
import { mockNavigator } from "./navigator";
import {
    MockBroadcastChannel,
    MockRequest,
    MockResponse,
    MockSharedWorker,
    MockURL,
    MockWebSocket,
    MockWorker,
    MockXMLHttpRequest,
    mockCookie,
    mockHistory,
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

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    document,
    Document,
    HTMLBodyElement,
    HTMLHeadElement,
    HTMLHtmlElement,
    innerHeight,
    innerWidth,
    MessagePort,
    Number: { isNaN: $isNaN, parseFloat: $parseFloat },
    Object: {
        defineProperty: $defineProperty,
        entries: $entries,
        getOwnPropertyDescriptor: $getOwnPropertyDescriptor,
        getPrototypeOf: $getPrototypeOf,
        hasOwn: $hasOwn,
    },
    ontouchstart,
    outerHeight,
    outerWidth,
    Reflect: { ownKeys: $ownKeys },
    Set,
    SharedWorker,
    Window,
    Worker,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {any} target
 * @param {Record<string, PropertyDescriptor>} descriptors
 */
const applyPropertyDescriptors = (target, descriptors) => {
    for (const [property, rawDescriptor] of $entries(descriptors)) {
        const owner = findPropertyOwner(target, property);
        originalDescriptors.push({
            descriptor: $getOwnPropertyDescriptor(owner, property),
            owner,
            property,
            target,
        });
        const descriptor = { ...rawDescriptor };
        if ("value" in descriptor) {
            descriptor.writable = false;
        }
        $defineProperty(owner, property, descriptor);
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
    if ($hasOwn(object, property)) {
        return object;
    }
    const prototype = $getPrototypeOf(object);
    if (prototype) {
        return findPropertyOwner(prototype, property);
    }
    return object;
};

const EVENT_TARGET_PROTOTYPES = new Map(
    [
        // Top level objects
        Window,
        Document,
        // Permanent DOM elements
        HTMLBodyElement,
        HTMLHeadElement,
        HTMLHtmlElement,
        // Workers
        MessagePort,
        SharedWorker,
        Worker,
        // Others
        EventBus,
    ].map((cls) => [cls.prototype, cls.prototype.addEventListener])
);

/** @type {{ descriptor: PropertyDescriptor; owner: any; property: string; target: any }[]} */
const originalDescriptors = [];

const mockLocalStorage = new MockStorage();
const mockSessionStorage = new MockStorage();
let mockTitle = "";

// Mock descriptors
const DOCUMENT_MOCK_DESCRIPTORS = {
    cookie: {
        get: () => mockCookie.get(),
        set: (value) => mockCookie.set(value),
    },
    title: {
        get: () => mockTitle,
        set: (value) => (mockTitle = value),
    },
};
const R_OWL_SYNTHETIC_LISTENER = /\bnativeToSyntheticEvent\b/;
const WINDOW_MOCK_DESCRIPTORS = {
    BroadcastChannel: { value: MockBroadcastChannel },
    cancelAnimationFrame: { value: mockedCancelAnimationFrame, writable: false },
    clearInterval: { value: mockedClearInterval, writable: false },
    clearTimeout: { value: mockedClearTimeout, writable: false },
    Date: { value: MockDate, writable: false },
    fetch: { value: mockedFetch, writable: false },
    history: { value: mockHistory },
    innerHeight: { get: () => getCurrentDimensions().height || innerHeight },
    innerWidth: { get: () => getCurrentDimensions().width || innerWidth },
    localStorage: { value: mockLocalStorage, writable: false },
    matchMedia: { value: mockedMatchMedia },
    navigator: { value: mockNavigator },
    Notification: { value: MockNotification },
    outerHeight: { get: () => getCurrentDimensions().height || outerHeight },
    outerWidth: { get: () => getCurrentDimensions().width || outerWidth },
    Request: { value: MockRequest, writable: false },
    requestAnimationFrame: { value: mockedRequestAnimationFrame, writable: false },
    Response: { value: MockResponse, writable: false },
    sessionStorage: { value: mockSessionStorage, writable: false },
    setInterval: { value: mockedSetInterval, writable: false },
    setTimeout: { value: mockedSetTimeout, writable: false },
    SharedWorker: { value: MockSharedWorker },
    URL: { value: MockURL },
    WebSocket: { value: MockWebSocket },
    Worker: { value: MockWorker },
    XMLHttpRequest: { value: MockXMLHttpRequest },
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupWindow() {
    // Storages
    mockLocalStorage.clear();
    mockSessionStorage.clear();

    // Title
    mockTitle = "";

    // Touch
    globalThis.ontouchstart = ontouchstart;
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
 * @param {boolean} setTouch
 */
export function mockTouch(setTouch) {
    if (setTouch) {
        globalThis.ontouchstart ||= null;
    } else {
        delete globalThis.ontouchstart;
    }
}

/**
 * @param {typeof globalThis} global
 */
export function patchWindow({ document, window } = globalThis) {
    applyPropertyDescriptors(window, WINDOW_MOCK_DESCRIPTORS);
    whenReady(() => {
        applyPropertyDescriptors(document, DOCUMENT_MOCK_DESCRIPTORS);
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

export function watchListeners() {
    const remaining = [];

    for (const [proto, addEventListener] of EVENT_TARGET_PROTOTYPES) {
        proto.addEventListener = function mockedAddEventListener(...args) {
            const runner = getRunner();
            if (runner.dry) {
                // Ignore listeners during dry run
                return;
            }
            if (runner.suiteStack.length && !R_OWL_SYNTHETIC_LISTENER.test(String(args[1]))) {
                // Do not cleanup:
                // - listeners outside of suites
                // - Owl synthetic listeners
                remaining.push([this, args]);
                runner.after(() => this.removeEventListener(...args));
            }
            return addEventListener.call(this, ...args);
        };
    }

    return function unwatchAllListeners() {
        while (remaining.length) {
            const [target, args] = remaining.pop();
            target.removeEventListener(...args);
        }

        for (const [proto, addEventListener] of EVENT_TARGET_PROTOTYPES) {
            proto.addEventListener = addEventListener;
        }
    };
}

/**
 * Returns a function checking that the given target does not contain any unexpected
 * key. The list of accepted keys is the initial list of keys of the target, along
 * with an optional `whiteList` argument.
 *
 * @template T
 * @param {T} target
 * @param {string[]} [whiteList]
 * @example
 *  afterEach(watchKeys(window, ["odoo"]));
 */
export function watchKeys(target, whiteList) {
    const acceptedKeys = new Set([...$ownKeys(target), ...(whiteList || [])]);

    return function checkKeys() {
        const keysDiff = $ownKeys(target).filter(
            (key) => $isNaN($parseFloat(key)) && !acceptedKeys.has(key)
        );
        for (const key of keysDiff) {
            const descriptor = $getOwnPropertyDescriptor(target, key);
            if (descriptor.configurable) {
                delete target[key];
            } else if (descriptor.writable) {
                target[key] = undefined;
            }
        }
    };
}
