/** @odoo-module */

import { whenReady } from "@odoo/owl";
import { mockedMatchMedia } from "@web/../lib/hoot-dom/helpers/dom";
import { MockMath } from "./math";
import { MockClipboard, mockNavigator } from "./navigator";
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

/** @type {{ descriptor: PropertyDescriptor; owner: any; property: string; target: any }[]} */
const originalDescriptors = [];

const mockClipboard = new MockClipboard();
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
export function patchWindow(global = globalThis) {
    applyPropertyDescriptors(global.window, WINDOW_MOCK_DESCRIPTORS);
    whenReady(() => {
        applyPropertyDescriptors(global.document, DOCUMENT_MOCK_DESCRIPTORS);
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

export function unpatchWindow() {
    for (const { descriptor, owner, property } of originalDescriptors) {
        Object.defineProperty(owner, property, descriptor);
    }
    originalDescriptors.length = 0;
}
