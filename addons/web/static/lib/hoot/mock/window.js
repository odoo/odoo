/** @odoo-module */

import { EventBus, whenReady } from "@odoo/owl";
import { getCurrentDimensions } from "@web/../lib/hoot-dom/helpers/dom";
import {
    mockedCancelAnimationFrame,
    mockedClearInterval,
    mockedClearTimeout,
    mockedRequestAnimationFrame,
    mockedSetInterval,
    mockedSetTimeout,
} from "@web/../lib/hoot-dom/helpers/time";
import { interactor } from "../../hoot-dom/hoot_dom_utils";
import { MockEventTarget, strictEqual } from "../hoot_utils";
import { getRunner } from "../main_runner";
import {
    MockAnimation,
    mockedAnimate,
    mockedScroll,
    mockedScrollBy,
    mockedScrollIntoView,
    mockedScrollTo,
    mockedWindowScroll,
    mockedWindowScrollBy,
    mockedWindowScrollTo,
} from "./animation";
import { MockConsole } from "./console";
import { MockDate, MockIntl } from "./date";
import { MockClipboardItem, mockNavigator } from "./navigator";
import {
    MockBroadcastChannel,
    MockMessageChannel,
    MockMessagePort,
    MockRequest,
    MockResponse,
    MockSharedWorker,
    MockURL,
    MockWebSocket,
    MockWorker,
    MockXMLHttpRequest,
    MockXMLHttpRequestUpload,
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
    Map,
    Number: { isNaN: $isNaN, parseFloat: $parseFloat },
    Object: {
        assign: $assign,
        defineProperty: $defineProperty,
        entries: $entries,
        getOwnPropertyDescriptor: $getOwnPropertyDescriptor,
        getPrototypeOf: $getPrototypeOf,
        keys: $keys,
        hasOwn: $hasOwn,
    },
    ontouchcancel,
    ontouchend,
    ontouchmove,
    ontouchstart,
    Reflect: { ownKeys: $ownKeys },
    Set,
    Window,
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
 * @param {string[]} [changedKeys]
 */
const callMediaQueryChanges = (changedKeys) => {
    for (const mediaQueryList of mediaQueryLists) {
        if (!changedKeys || changedKeys.some((key) => mediaQueryList.media.includes(key))) {
            const event = new MediaQueryListEvent("change", {
                matches: mediaQueryList.matches,
                media: mediaQueryList.media,
            });
            mediaQueryList.dispatchEvent(event);
        }
    }
};

/**
 * @template T
 * @param {T} target
 * @param {keyof T} property
 */
const findOriginalDescriptor = (target, property) => {
    for (const od of originalDescriptors) {
        if (od.target === target && od.property === property) {
            return od.descriptor;
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

/**
 * @param {string} mediaQueryString
 */
const matchesQueryPart = (mediaQueryString) => {
    const [, key, value] = mediaQueryString.match(R_MEDIA_QUERY_PROPERTY) || [];
    let match = false;
    if (mockMediaValues[key]) {
        match = strictEqual(value, mockMediaValues[key]);
    } else if (key) {
        switch (key) {
            case "max-height": {
                match = getCurrentDimensions().height <= $parseFloat(value);
                break;
            }
            case "max-width": {
                match = getCurrentDimensions().width <= $parseFloat(value);
                break;
            }
            case "min-height": {
                match = getCurrentDimensions().height >= $parseFloat(value);
                break;
            }
            case "min-width": {
                match = getCurrentDimensions().width >= $parseFloat(value);
                break;
            }
            case "orientation": {
                const { width, height } = getCurrentDimensions();
                match = value === "landscape" ? width > height : width < height;
                break;
            }
        }
    }
    return mediaQueryString.startsWith("not") ? !match : match;
};

function mockedElementFromPoint(...args) {
    return mockedElementsFromPoint.call(this, ...args)[0];
}

/**
 * Mocked version of {@link document.elementsFromPoint} to:
 * - remove "HOOT-..." elements from the result
 * - put the <body> & <html> elements at the end of the list, as they may be ordered
 *  incorrectly due to the fixture being behind the body.
 */
function mockedElementsFromPoint(...args) {
    const { value: elementsFromPoint } = findOriginalDescriptor(this, "elementsFromPoint");
    const result = [];
    let hasDocumentElement = false;
    let hasBody = false;
    for (const element of elementsFromPoint.call(this, ...args)) {
        if (element.tagName.startsWith("HOOT")) {
            continue;
        }
        if (element === this.body) {
            hasBody = true;
        } else if (element === this.documentElement) {
            hasDocumentElement = true;
        } else {
            result.push(element);
        }
    }
    if (hasBody) {
        result.push(this.body);
    }
    if (hasDocumentElement) {
        result.push(this.documentElement);
    }
    return result;
}

/**
 * @type {typeof matchMedia}
 */
const mockedMatchMedia = (mediaQueryString) => new MockMediaQueryList(mediaQueryString);

class MockMediaQueryList extends MockEventTarget {
    static publicListeners = ["change"];

    get matches() {
        return this.media
            .split(R_COMMA)
            .some((orPart) => orPart.split(R_AND).every(matchesQueryPart));
    }

    /**
     * @param {string} mediaQueryString
     */
    constructor(mediaQueryString) {
        super(...arguments);

        this.media = mediaQueryString.trim().toLowerCase();

        mediaQueryLists.add(this);
    }
}

const DEFAULT_MEDIA_VALUES = {
    "display-mode": "browser",
    pointer: "fine",
    "prefers-color-scheme": "light",
    "prefers-reduced-motion": "reduce",
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
        // Other event targets
        EventBus,
        MockEventTarget,
    ].map(({ prototype }) => [
        prototype,
        [prototype.addEventListener, prototype.removeEventListener],
    ])
);

const R_AND = /\s*\band\b\s*/;
const R_COMMA = /\s*,\s*/;
const R_MEDIA_QUERY_PROPERTY = /\(\s*([\w-]+)\s*:\s*(.+)\s*\)/;

/** @type {{ descriptor: PropertyDescriptor; owner: any; property: string; target: any }[]} */
const originalDescriptors = [];

/** @type {Set<MockMediaQueryList>} */
const mediaQueryLists = new Set();
const mockConsole = new MockConsole();
const mockLocalStorage = new MockStorage();
const mockMediaValues = { ...DEFAULT_MEDIA_VALUES };
const mockSessionStorage = new MockStorage();
let mockTitle = "";

const R_OWL_SYNTHETIC_LISTENER = /\bnativeToSyntheticEvent\b/;

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
const ELEMENT_MOCK_DESCRIPTORS = {
    animate: { value: mockedAnimate },
    scroll: { value: mockedScroll },
    scrollBy: { value: mockedScrollBy },
    scrollIntoView: { value: mockedScrollIntoView },
    scrollTo: { value: mockedScrollTo },
};
const WINDOW_MOCK_DESCRIPTORS = {
    Animation: { value: MockAnimation },
    Blob: { value: MockBlob },
    BroadcastChannel: { value: MockBroadcastChannel },
    cancelAnimationFrame: { value: mockedCancelAnimationFrame, writable: false },
    clearInterval: { value: mockedClearInterval, writable: false },
    clearTimeout: { value: mockedClearTimeout, writable: false },
    ClipboardItem: { value: MockClipboardItem },
    console: { value: mockConsole, writable: false },
    Date: { value: MockDate, writable: false },
    EventTarget: { value: MockEventTarget },
    fetch: { value: interactor("server", mockedFetch).as("fetch"), writable: false },
    history: { value: mockHistory },
    innerHeight: { get: () => getCurrentDimensions().height },
    innerWidth: { get: () => getCurrentDimensions().width },
    Intl: { value: MockIntl },
    localStorage: { value: mockLocalStorage, writable: false },
    matchMedia: { value: mockedMatchMedia },
    MessageChannel: { value: MockMessageChannel },
    MessagePort: { value: MockMessagePort },
    navigator: { value: mockNavigator },
    Notification: { value: MockNotification },
    outerHeight: { get: () => getCurrentDimensions().height },
    outerWidth: { get: () => getCurrentDimensions().width },
    Request: { value: MockRequest, writable: false },
    requestAnimationFrame: { value: mockedRequestAnimationFrame, writable: false },
    Response: { value: MockResponse, writable: false },
    scroll: { value: mockedWindowScroll },
    scrollBy: { value: mockedWindowScrollBy },
    scrollTo: { value: mockedWindowScrollTo },
    sessionStorage: { value: mockSessionStorage, writable: false },
    setInterval: { value: mockedSetInterval, writable: false },
    setTimeout: { value: mockedSetTimeout, writable: false },
    SharedWorker: { value: MockSharedWorker },
    URL: { value: MockURL },
    WebSocket: { value: MockWebSocket },
    Worker: { value: MockWorker },
    XMLHttpRequest: { value: MockXMLHttpRequest },
    XMLHttpRequestUpload: { value: MockXMLHttpRequestUpload },
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupWindow() {
    // Storages
    mockLocalStorage.clear();
    mockSessionStorage.clear();

    // Media
    mediaQueryLists.clear();
    $assign(mockMediaValues, DEFAULT_MEDIA_VALUES);

    // Title
    mockTitle = "";

    // Body & head attributes
    for (const { name } of document.head.attributes) {
        document.head.removeAttribute(name);
    }
    for (const { name } of document.body.attributes) {
        document.body.removeAttribute(name);
    }

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
 * @param {Record<string, string>} name
 */
export function mockMatchMedia(values) {
    $assign(mockMediaValues, values);

    callMediaQueryChanges($keys(values));
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

    mockMatchMedia({ pointer: setTouch ? "coarse" : "fine" });
}

/**
 * @param {typeof globalThis} global
 */
export function patchWindow({ document, window } = globalThis) {
    applyPropertyDescriptors(window, WINDOW_MOCK_DESCRIPTORS);
    applyPropertyDescriptors(window.Element.prototype, ELEMENT_MOCK_DESCRIPTORS);
    whenReady(() => {
        applyPropertyDescriptors(document, DOCUMENT_MOCK_DESCRIPTORS);
    });

    window.addEventListener("resize", () => callMediaQueryChanges());
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
    /**
     * @param {WeakRef<EventTarget>} targetRef
     */
    const removeRefListener = (targetRef) => {
        if (!listenerRefs.has(targetRef)) {
            return;
        }
        const [removeEventListener, args] = listenerRefs.get(targetRef);
        listenerRefs.delete(targetRef);
        const target = targetRef.deref();
        if (target) {
            removeEventListener.call(target, ...args);
        }
    };

    /** @type {Map<WeakRef<EventTarget>, [EventTarget["removeEventListener"], any[]]>} */
    const listenerRefs = new Map();
    const runner = getRunner();

    for (const [proto, [addEventListener, removeEventListener]] of EVENT_TARGET_PROTOTYPES) {
        proto.addEventListener = function mockedAddEventListener(...args) {
            if (runner.dry) {
                // Ignore listeners during dry run
                return;
            }
            if (runner.suiteStack.length && !R_OWL_SYNTHETIC_LISTENER.test(String(args[1]))) {
                // Do not cleanup:
                // - listeners outside of suites
                // - Owl synthetic listeners
                const ref = new WeakRef(this);
                listenerRefs.set(ref, [removeEventListener, args]);
                runner.after(() => removeRefListener(ref));
            }
            return addEventListener.call(this, ...args);
        };
        proto.removeEventListener = function mockedRemoveEventListener(...args) {
            if (runner.dry) {
                // Ignore listeners during dry run
                return;
            }
            return removeEventListener.call(this, ...args);
        };
    }

    return function unwatchAllListeners() {
        for (const ref of listenerRefs.keys()) {
            removeRefListener(ref);
        }

        for (const [proto, [addEventListener, removeEventListener]] of EVENT_TARGET_PROTOTYPES) {
            proto.addEventListener = addEventListener;
            proto.removeEventListener = removeEventListener;
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
