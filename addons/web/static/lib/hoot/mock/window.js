/** @odoo-module */

import { EventBus, whenReady } from "@odoo/owl";
import { getCurrentDimensions, mockedMatchMedia } from "@web/../lib/hoot-dom/helpers/dom";
import {
    mockedCancelAnimationFrame,
    mockedClearInterval,
    mockedClearTimeout,
    mockedRequestAnimationFrame,
    mockedSetInterval,
    mockedSetTimeout,
} from "@web/../lib/hoot-dom/helpers/time";
import { getRunner } from "../main_runner";
import { MockConsole } from "./console";
import { MockDate } from "./date";
import { MockClipboardItem, mockNavigator } from "./navigator";
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
import { MockBlob } from "./sync_values";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    document,
    Document,
    HTMLBodyElement,
    HTMLHeadElement,
    HTMLHtmlElement,
    MessagePort,
    Number: { isNaN: $isNaN, parseFloat: $parseFloat },
    Object: {
        defineProperty: $defineProperty,
        entries: $entries,
        getOwnPropertyDescriptor: $getOwnPropertyDescriptor,
        getPrototypeOf: $getPrototypeOf,
        hasOwn: $hasOwn,
    },
    ontouchcancel,
    ontouchend,
    ontouchmove,
    ontouchstart,
    Reflect: { ownKeys: $ownKeys },
    Set,
    SharedWorker,
    Window,
    Worker,
} = globalThis;

const touchFunctions = { ontouchcancel, ontouchend, ontouchmove, ontouchstart };

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

function mockedElementFromPoint() {
    return mockedElementsFromPoint.call(this, ...arguments)[0];
}

function mockedElementsFromPoint() {
    const { value: elementsFromPoint } = findOriginalDescriptor(document, "elementsFromPoint");
    const elements = elementsFromPoint
        .call(this, ...arguments)
        .filter(
            (el) =>
                !el.tagName.startsWith("HOOT") && el !== this.body && el !== this.documentElement
        );
    elements.push(this.body, this.documentElement);
    return elements;
}

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
    ].map(({ prototype }) => [
        prototype,
        [prototype.addEventListener, prototype.removeEventListener],
    ])
);

/** @type {{ descriptor: PropertyDescriptor; owner: any; property: string; target: any }[]} */
const originalDescriptors = [];

const mockConsole = new MockConsole();
const mockLocalStorage = new MockStorage();
const mockSessionStorage = new MockStorage();
let mockTitle = "";

// Mock descriptors
const DOCUMENT_MOCK_DESCRIPTORS = {
    cookie: {
        get: () => mockCookie.get(),
        set: (value) => mockCookie.set(value),
    },
    elementFromPoint: { value: mockedElementFromPoint },
    elementsFromPoint: { value: mockedElementsFromPoint },
    title: {
        get: () => mockTitle,
        set: (value) => (mockTitle = value),
    },
};
const R_OWL_SYNTHETIC_LISTENER = /\bnativeToSyntheticEvent\b/;
const WINDOW_MOCK_DESCRIPTORS = {
    Blob: { value: MockBlob },
    BroadcastChannel: { value: MockBroadcastChannel },
    cancelAnimationFrame: { value: mockedCancelAnimationFrame, writable: false },
    clearInterval: { value: mockedClearInterval, writable: false },
    clearTimeout: { value: mockedClearTimeout, writable: false },
    console: { value: mockConsole, writable: false },
    ClipboardItem: { value: MockClipboardItem },
    Date: { value: MockDate, writable: false },
    fetch: { value: mockedFetch, writable: false },
    history: { value: mockHistory },
    innerHeight: { get: () => getCurrentDimensions().height },
    innerWidth: { get: () => getCurrentDimensions().width },
    localStorage: { value: mockLocalStorage, writable: false },
    matchMedia: { value: mockedMatchMedia },
    navigator: { value: mockNavigator },
    Notification: { value: MockNotification },
    outerHeight: { get: () => getCurrentDimensions().height },
    outerWidth: { get: () => getCurrentDimensions().width },
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
    for (const [fnName, originalFn] of $entries(touchFunctions)) {
        globalThis[fnName] = originalFn;
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

export function getViewPortHeight() {
    const heightDescriptor = findOriginalDescriptor(window, "innerHeight");
    if (heightDescriptor) {
        return heightDescriptor.get.call(window);
    } else {
        return window.innerHeight;
    }
}

export function getViewPortWidth() {
    const titleDescriptor = findOriginalDescriptor(window, "innerWidth");
    if (titleDescriptor) {
        return titleDescriptor.get.call(window);
    } else {
        return window.innerWidth;
    }
}

/**
 * @param {boolean} setTouch
 * @param {typeof globalThis} [window=globalThis]
 */
export function mockTouch(setTouch, { Document, HTMLElement, SVGElement } = globalThis) {
    const prototypes = [Document.prototype, HTMLElement.prototype, SVGElement.prototype];
    if (setTouch) {
        for (const fnName in touchFunctions) {
            globalThis[fnName] ??= null;
            for (const proto of prototypes) {
                if (!(fnName in proto)) {
                    proto[fnName] = null;
                }
            }
        }
    } else {
        for (const fnName in touchFunctions) {
            delete globalThis[fnName];
            for (const proto of prototypes) {
                delete proto[fnName];
            }
        }
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

    for (const [proto, [addEventListener, removeEventListener]] of EVENT_TARGET_PROTOTYPES) {
        proto.addEventListener = function mockedAddEventListener(...args) {
            const runner = getRunner();
            if (runner.dry) {
                // Ignore listeners during dry run
                return;
            }
            if (runner.suiteStack.length && !R_OWL_SYNTHETIC_LISTENER.test(String(args[1]))) {
                const cleanup = removeEventListener.bind(this, ...args);
                // Do not cleanup:
                // - listeners outside of suites
                // - Owl synthetic listeners
                remaining.push(cleanup);
                runner.after(cleanup);
            }
            return addEventListener.call(this, ...args);
        };
    }

    return function unwatchAllListeners() {
        while (remaining.length) {
            remaining.pop()();
        }

        for (const [proto, [addEventListener]] of EVENT_TARGET_PROTOTYPES) {
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
