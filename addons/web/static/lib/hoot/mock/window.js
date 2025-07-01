/** @odoo-module */

import { EventBus, whenReady } from "@odoo/owl";
import { getCurrentDimensions, getDocument, getWindow } from "@web/../lib/hoot-dom/helpers/dom";
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
    mockLocation,
    mockedFetch,
} from "./network";
import { MockNotification } from "./notification";
import { MockStorage } from "./storage";
import { MockBlob } from "./sync_values";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    EventTarget,
    HTMLAnchorElement,
    Number: { isNaN: $isNaN, parseFloat: $parseFloat },
    Object: {
        assign: $assign,
        defineProperties: $defineProperties,
        entries: $entries,
        getOwnPropertyDescriptor: $getOwnPropertyDescriptor,
        getPrototypeOf: $getPrototypeOf,
        keys: $keys,
        hasOwn: $hasOwn,
    },
    Reflect: { ownKeys: $ownKeys },
    Set,
    WeakMap,
} = globalThis;

const { addEventListener, removeEventListener } = EventTarget.prototype;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {unknown} target
 * @param {Record<string, PropertyDescriptor>} descriptors
 */
function applyPropertyDescriptors(target, descriptors) {
    if (!originalDescriptors.has(target)) {
        originalDescriptors.set(target, {});
    }
    const targetDescriptors = originalDescriptors.get(target);
    const ownerDecriptors = new Map();
    for (const [property, rawDescriptor] of $entries(descriptors)) {
        const owner = findPropertyOwner(target, property);
        targetDescriptors[property] = $getOwnPropertyDescriptor(owner, property);
        const descriptor = { ...rawDescriptor };
        if ("value" in descriptor) {
            descriptor.writable = false;
        }
        if (!ownerDecriptors.has(owner)) {
            ownerDecriptors.set(owner, {});
        }
        const nextDescriptors = ownerDecriptors.get(owner);
        nextDescriptors[property] = descriptor;
    }
    for (const [owner, nextDescriptors] of ownerDecriptors) {
        $defineProperties(owner, nextDescriptors);
    }
}

/**
 * @param {string[]} [changedKeys]
 */
function callMediaQueryChanges(changedKeys) {
    for (const mediaQueryList of mediaQueryLists) {
        if (!changedKeys || changedKeys.some((key) => mediaQueryList.media.includes(key))) {
            const event = new MediaQueryListEvent("change", {
                matches: mediaQueryList.matches,
                media: mediaQueryList.media,
            });
            mediaQueryList.dispatchEvent(event);
        }
    }
}

/**
 * @template T
 * @param {T} target
 * @param {keyof T} property
 */
function findOriginalDescriptor(target, property) {
    if (originalDescriptors.has(target)) {
        const descriptors = originalDescriptors.get(target);
        if (descriptors && property in descriptors) {
            return descriptors[property];
        }
    }
    return null;
}

/**
 * @param {unknown} object
 * @param {string} property
 * @returns {unknown}
 */
function findPropertyOwner(object, property) {
    if ($hasOwn(object, property)) {
        return object;
    }
    const prototype = $getPrototypeOf(object);
    if (prototype) {
        return findPropertyOwner(prototype, property);
    }
    return object;
}

/**
 * @param {unknown} object
 */
function getTouchDescriptors(object) {
    const descriptors = {};
    const toDelete = [];
    for (const eventName of TOUCH_EVENTS) {
        const fnName = `on${eventName}`;
        if (fnName in object) {
            const owner = findPropertyOwner(object, fnName);
            descriptors[fnName] = $getOwnPropertyDescriptor(owner, fnName);
        } else {
            toDelete.push(fnName);
        }
    }
    /** @type {({ descriptors?: Record<string, PropertyDescriptor>; toDelete?: string[]})} */
    const result = {};
    if ($keys(descriptors).length) {
        result.descriptors = descriptors;
    }
    if (toDelete.length) {
        result.toDelete = toDelete;
    }
    return result;
}

/**
 * @param {typeof globalThis} view
 */
function getTouchTargets(view) {
    return [view, view.Document.prototype];
}

/**
 * @param {typeof globalThis} view
 */
function getWatchedEventTargets(view) {
    return [
        view,
        view.document,
        // Permanent DOM elements
        view.HTMLDocument.prototype,
        view.HTMLBodyElement.prototype,
        view.HTMLHeadElement.prototype,
        view.HTMLHtmlElement.prototype,
        // Other event targets
        EventBus.prototype,
        MockEventTarget.prototype,
    ];
}

/**
 * @param {string} type
 * @returns {PropertyDescriptor}
 */
function makeEventDescriptor(type) {
    let callback = null;
    return {
        enumerable: true,
        configurable: true,
        get() {
            return callback;
        },
        set(value) {
            if (callback === value) {
                return;
            }
            if (typeof callback === "function") {
                this.removeEventListener(type, callback);
            }
            callback = value;
            if (typeof callback === "function") {
                this.addEventListener(type, callback);
            }
        },
    };
}

/**
 * @param {string} mediaQueryString
 */
function matchesQueryPart(mediaQueryString) {
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
}

/** @type {addEventListener} */
function mockedAddEventListener(...args) {
    const runner = getRunner();
    if (runner.dry || !runner.suiteStack.length) {
        // Ignore listeners during dry run or outside of a test suite
        return;
    }
    if (!R_OWL_SYNTHETIC_LISTENER.test(String(args[1]))) {
        // Ignore cleanup for Owl synthetic listeners
        runner.after(removeEventListener.bind(this, ...args));
    }
    return addEventListener.call(this, ...args);
}

/** @type {Document["elementFromPoint"]} */
function mockedElementFromPoint(...args) {
    return mockedElementsFromPoint.call(this, ...args)[0];
}

/**
 * Mocked version of {@link document.elementsFromPoint} to:
 * - remove "HOOT-..." elements from the result
 * - put the <body> & <html> elements at the end of the list, as they may be ordered
 *  incorrectly due to the fixture being behind the body.
 * @type {Document["elementsFromPoint"]}
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

function mockedHref() {
    return this.hasAttribute("href") ? new MockURL(this.getAttribute("href")).href : "";
}

/** @type {typeof matchMedia} */
function mockedMatchMedia(mediaQueryString) {
    return new MockMediaQueryList(mediaQueryString);
}

/** @type {typeof removeEventListener} */
function mockedRemoveEventListener(...args) {
    if (getRunner().dry) {
        // Ignore listeners during dry run
        return;
    }
    return removeEventListener.call(this, ...args);
}

/**
 * @param {PointerEvent} ev
 */
function onAnchorHrefClick(ev) {
    if (ev.defaultPrevented) {
        return;
    }
    const href = ev.target.closest("a[href]")?.href;
    if (!href) {
        return;
    }

    ev.preventDefault();

    // Assign href to mock location instead of actual location
    mockLocation.href = href;

    const [, hash] = href.split("#");
    if (hash) {
        // Scroll to the target element if the href is/has a hash
        getDocument().getElementById(hash)?.scrollIntoView();
    }
}

function onWindowResize() {
    callMediaQueryChanges();
}

/**
 * @param {typeof globalThis} view
 */
function restoreTouch(view) {
    const touchObjects = getTouchTargets(view);
    for (let i = 0; i < touchObjects.length; i++) {
        const object = touchObjects[i];
        const { descriptors, toDelete } = originalTouchFunctions[i];
        if (descriptors) {
            $defineProperties(object, descriptors);
        }
        if (toDelete) {
            for (const fnName of toDelete) {
                delete object[fnName];
            }
        }
    }
}

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

const TOUCH_EVENTS = ["touchcancel", "touchend", "touchmove", "touchstart"];

const R_AND = /\s*\band\b\s*/;
const R_COMMA = /\s*,\s*/;
const R_MEDIA_QUERY_PROPERTY = /\(\s*([\w-]+)\s*:\s*(.+)\s*\)/;
const R_OWL_SYNTHETIC_LISTENER = /\bnativeToSyntheticEvent\b/;

/** @type {WeakMap<unknown, Record<string, PropertyDescriptor>>} */
const originalDescriptors = new WeakMap();
const originalTouchFunctions = getTouchTargets(globalThis).map(getTouchDescriptors);

/** @type {Set<MockMediaQueryList>} */
const mediaQueryLists = new Set();
const mockConsole = new MockConsole();
const mockLocalStorage = new MockStorage();
const mockMediaValues = { ...DEFAULT_MEDIA_VALUES };
const mockSessionStorage = new MockStorage();
let mockTitle = "";

// Mock descriptors
const ANCHOR_MOCK_DESCRIPTORS = {
    href: {
        ...$getOwnPropertyDescriptor(HTMLAnchorElement.prototype, "href"),
        get: mockedHref,
    },
};
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
    const view = getWindow();

    // Storages
    mockLocalStorage.clear();
    mockSessionStorage.clear();

    // Media
    mediaQueryLists.clear();
    $assign(mockMediaValues, DEFAULT_MEDIA_VALUES);

    // Title
    mockTitle = "";

    // Listeners
    view.removeEventListener("click", onAnchorHrefClick);
    view.removeEventListener("resize", onWindowResize);

    // Head & body attributes
    const { head, body } = view.document;
    for (const { name } of head.attributes) {
        head.removeAttribute(name);
    }
    for (const { name } of body.attributes) {
        body.removeAttribute(name);
    }

    // Touch
    restoreTouch(view);
}

export function getTitle() {
    const doc = getDocument();
    const titleDescriptor = findOriginalDescriptor(doc, "title");
    if (titleDescriptor) {
        return titleDescriptor.get.call(doc);
    } else {
        return doc.title;
    }
}

export function getViewPortHeight() {
    const view = getWindow();
    const heightDescriptor = findOriginalDescriptor(view, "innerHeight");
    if (heightDescriptor) {
        return heightDescriptor.get.call(view);
    } else {
        return view.innerHeight;
    }
}

export function getViewPortWidth() {
    const view = getWindow();
    const titleDescriptor = findOriginalDescriptor(view, "innerWidth");
    if (titleDescriptor) {
        return titleDescriptor.get.call(view);
    } else {
        return view.innerWidth;
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
 */
export function mockTouch(setTouch) {
    const objects = getTouchTargets(getWindow());
    if (setTouch) {
        for (const object of objects) {
            const descriptors = {};
            for (const eventName of TOUCH_EVENTS) {
                const fnName = `on${eventName}`;
                if (!$hasOwn(object, fnName)) {
                    descriptors[fnName] = makeEventDescriptor(eventName);
                }
            }
            $defineProperties(object, descriptors);
        }
        mockMatchMedia({ pointer: "coarse" });
    } else {
        for (const object of objects) {
            for (const eventName of TOUCH_EVENTS) {
                delete object[`on${eventName}`];
            }
        }
        mockMatchMedia({ pointer: "fine" });
    }
}

/**
 * @param {typeof globalThis} [view=getWindow()]
 */
export function patchWindow(view = getWindow()) {
    // Window (doesn't need to be ready)
    applyPropertyDescriptors(view, WINDOW_MOCK_DESCRIPTORS);

    whenReady(() => {
        // Document
        applyPropertyDescriptors(view.document, DOCUMENT_MOCK_DESCRIPTORS);

        // Element prototypes
        applyPropertyDescriptors(view.Element.prototype, ELEMENT_MOCK_DESCRIPTORS);
        applyPropertyDescriptors(view.HTMLAnchorElement.prototype, ANCHOR_MOCK_DESCRIPTORS);
    });
}

/**
 * @param {string} value
 */
export function setTitle(value) {
    const doc = getDocument();
    const titleDescriptor = findOriginalDescriptor(doc, "title");
    if (titleDescriptor) {
        titleDescriptor.set.call(doc, value);
    } else {
        doc.title = value;
    }
}

export function setupWindow() {
    const view = getWindow();

    // Listeners
    view.addEventListener("click", onAnchorHrefClick);
    view.addEventListener("resize", onWindowResize);
}

export function watchListeners() {
    const targets = getWatchedEventTargets(getWindow());
    for (const target of targets) {
        target.addEventListener = mockedAddEventListener;
        target.removeEventListener = mockedRemoveEventListener;
    }

    return function unwatchAllListeners() {
        for (const target of targets) {
            target.addEventListener = addEventListener;
            target.removeEventListener = removeEventListener;
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
