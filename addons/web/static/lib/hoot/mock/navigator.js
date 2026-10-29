/** @odoo-module */

import { isInstanceOf } from "../../hoot-dom/hoot_dom_utils";
import {
    createMock,
    getSyncValue,
    HootError,
    MIME_TYPE,
    MockEventTarget,
    setSyncValue,
} from "../hoot_utils";
import { ensureTest } from "../main_runner";

/**
 * @typedef {"android" | "ios" | "linux" | "mac" | "windows"} Platform
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Blob,
    ClipboardItem = class NonSecureClipboardItem {},
    DOMException,
    navigator,
    Object: { assign: $assign, entries: $entries },
    queueMicrotask,
    Set,
    TypeError,
} = globalThis;
const { userAgent: $userAgent } = navigator;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

function getBlobValue(value) {
    return isInstanceOf(value, Blob) ? value.text() : value;
}

/**
 * Returns the final synchronous value of several item types.
 *
 * @param {unknown} value
 * @param {string} type
 */
function getClipboardValue(value, type) {
    return getBlobValue(isInstanceOf(value, ClipboardItem) ? value.getType(type) : value);
}

function getMockValues() {
    return {
        sendBeacon: throwNotImplemented("sendBeacon"),
        userAgent: makeUserAgent("linux"),
        /** @type {Navigator["vibrate"]} */
        vibrate: throwNotImplemented("vibrate"),
    };
}

/**
 * Returns the descriptors of the mocked permission-gated APIs, only for those that
 * are natively available, to keep feature detection intact (e.g. `if (navigator.x)`).
 */
function getPermissionGatedDescriptors() {
    const mocks = {
        credentials: new MockCredentialsContainer(),
        geolocation: new MockGeolocation(),
        storage: new MockStorageManager(),
        wakeLock: new MockWakeLock(),
    };
    /** @type {Record<string, PropertyDescriptor>} */
    const descriptors = {};
    for (const [name, value] of $entries(mocks)) {
        if (name in navigator) {
            descriptors[name] = { value };
        }
    }
    return descriptors;
}

/**
 * @returns {Record<PermissionName, { name: string; state: PermissionState }>}
 */
function getPermissions() {
    return {
        "background-sync": {
            state: "granted", // should always be granted
            name: "background_sync",
        },
        "local-fonts": {
            state: "denied",
            name: "local_fonts",
        },
        "payment-handler": {
            state: "denied",
            name: "payment_handler",
        },
        "persistent-storage": {
            state: "denied",
            name: "durable_storage",
        },
        "screen-wake-lock": {
            state: "denied",
            name: "screen_wake_lock",
        },
        "storage-access": {
            state: "denied",
            name: "storage-access",
        },
        "window-management": {
            state: "denied",
            name: "window_placement",
        },
        accelerometer: {
            state: "denied",
            name: "sensors",
        },
        camera: {
            state: "denied",
            name: "video_capture",
        },
        geolocation: {
            state: "denied",
            name: "geolocation",
        },
        gyroscope: {
            state: "denied",
            name: "sensors",
        },
        magnetometer: {
            state: "denied",
            name: "sensors",
        },
        microphone: {
            state: "denied",
            name: "audio_capture",
        },
        midi: {
            state: "denied",
            name: "midi",
        },
        notifications: {
            state: "denied",
            name: "notifications",
        },
        push: {
            state: "denied",
            name: "push",
        },
    };
}

function getUserAgentBrowser() {
    if (/Firefox/i.test($userAgent)) {
        return "Gecko/20100101 Firefox/1000.0"; // Firefox
    }
    if (/Chrome/i.test($userAgent)) {
        return "AppleWebKit/1000.00 (KHTML, like Gecko) Chrome/1000.00 Safari/1000.00"; // Chrome
    }
    if (/Safari/i.test($userAgent)) {
        return "AppleWebKit/1000.00 (KHTML, like Gecko) Version/1000.00 Safari/1000.00"; // Safari
    }
}

/**
 * @param {Platform} platform
 */
function makeUserAgent(platform) {
    const userAgent = ["Mozilla/5.0"];
    switch (platform.toLowerCase()) {
        case "android": {
            userAgent.push("(Linux; Android 1000)");
            break;
        }
        case "ios": {
            userAgent.push("(iPhone; CPU iPhone OS 1000_0 like Mac OS X)");
            break;
        }
        case "linux": {
            userAgent.push("(X11; Linux x86_64)");
            break;
        }
        case "mac":
        case "macintosh": {
            userAgent.push("(Macintosh; Intel Mac OS X 10_15_7)");
            break;
        }
        case "win":
        case "windows": {
            userAgent.push("(Windows NT 10.0; Win64; x64)");
            break;
        }
        default: {
            userAgent.push(platform);
        }
    }
    if (userAgentBrowser) {
        userAgent.push(userAgentBrowser);
    }
    return userAgent.join(" ");
}

/**
 * @param {string} apiName
 */
function notAllowed(apiName) {
    return new DOMException(
        `${apiName}: not allowed in tests (mock it to provide actual results)`,
        "NotAllowedError"
    );
}

/**
 * @param {PositionErrorCallback | null} [errorCallback]
 */
function rejectPosition(errorCallback) {
    if (typeof errorCallback !== "function") {
        return;
    }
    const code =
        currentPermissions.geolocation.state === "granted"
            ? GEOLOCATION_ERROR_CODES.POSITION_UNAVAILABLE
            : GEOLOCATION_ERROR_CODES.PERMISSION_DENIED;
    const error = {
        ...GEOLOCATION_ERROR_CODES,
        code,
        message: "navigator.geolocation: no position available in tests",
    };
    // Native callbacks are always called asynchronously
    queueMicrotask(() => errorCallback(error));
}

/**
 * @param {PermissionName} name
 * @param {PermissionState} value
 */
function setPermission(name, value) {
    const permission = currentPermissions[name];
    permission.state = value;
    for (const permissionStatus of permissionStatuses) {
        if (permissionStatus._permission === permission) {
            permissionStatus.dispatchEvent(new Event("change"));
        }
    }
}

/**
 * @param {string} fnName
 */
function throwNotImplemented(fnName) {
    return function notImplemented() {
        throw new HootError(`unmocked navigator method: ${fnName}`);
    };
}

const GEOLOCATION_ERROR_CODES = {
    PERMISSION_DENIED: 1,
    POSITION_UNAVAILABLE: 2,
    TIMEOUT: 3,
};

/** @type {Set<MockPermissionStatus>} */
const permissionStatuses = new Set();
let geolocationWatchId = 0;
const userAgentBrowser = getUserAgentBrowser();
const mockValues = getMockValues();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockClipboard {
    /** @type {unknown} */
    _value = null;

    async read() {
        return this._value;
    }

    async readText() {
        return String(getClipboardValue(this._value, MIME_TYPE.text) ?? "");
    }

    async write(value) {
        this._value = value;
    }

    async writeText(value) {
        this._value = String(getClipboardValue(value, MIME_TYPE.text) ?? "");
    }
}

export class MockClipboardItem extends ClipboardItem {
    constructor(items) {
        super(items);

        setSyncValue(this, items);
    }

    // Added synchronous methods to enhance speed in tests

    async getType(type) {
        return getSyncValue(this, false)[type];
    }
}

/**
 * Permission-gated APIs (credentials, geolocation, storage, wake lock) are mocked
 * to behave as if their permission were not granted: production code has to handle
 * that case anyway, and no prompt nor actual device/storage access is triggered.
 * Tests requiring actual results are expected to patch them.
 */
export class MockCredentialsContainer {
    async create() {
        throw notAllowed("navigator.credentials.create");
    }

    async get() {
        throw notAllowed("navigator.credentials.get");
    }

    async preventSilentAccess() {}

    async store() {
        throw notAllowed("navigator.credentials.store");
    }
}

export class MockGeolocation {
    /**
     * @param {number} _watchId
     */
    clearWatch(_watchId) {}

    /**
     * @param {PositionCallback} _successCallback
     * @param {PositionErrorCallback | null} [errorCallback]
     */
    getCurrentPosition(_successCallback, errorCallback) {
        rejectPosition(errorCallback);
    }

    /**
     * @param {PositionCallback} _successCallback
     * @param {PositionErrorCallback | null} [errorCallback]
     */
    watchPosition(_successCallback, errorCallback) {
        rejectPosition(errorCallback);
        return ++geolocationWatchId;
    }
}

export class MockPermissions {
    /**
     * @param {PermissionDescriptor} permissionDesc
     */
    async query({ name }) {
        if (!(name in currentPermissions)) {
            throw new TypeError(
                `The provided value '${name}' is not a valid enum value of type PermissionName`
            );
        }
        return new MockPermissionStatus(name);
    }
}

export class MockPermissionStatus extends MockEventTarget {
    static publicListeners = ["change"];

    /** @type {typeof currentPermissions[PermissionName]} */
    _permission;

    /**
     * @param {PermissionName} name
     * @param {PermissionState} value
     */
    constructor(name) {
        super(...arguments);

        this._permission = currentPermissions[name];
        permissionStatuses.add(this);
    }

    get name() {
        return this._permission.name;
    }

    get state() {
        return this._permission.state;
    }
}

export class MockServiceWorker extends MockEventTarget {
    static publicListeners = ["error", "message"];

    /** @type {ServiceWorkerState} */
    state = "activated";

    /**
     * @param {string} scriptURL
     */
    constructor(scriptURL) {
        super(...arguments);

        /** @type {string} */
        this.scriptURL = scriptURL;
    }

    /**
     * @param {any} _message
     */
    postMessage(_message) {}
}

export class MockServiceWorkerContainer extends MockEventTarget {
    static publicListeners = ["controllerchange", "message", "messageerror"];

    /**
     * @private
     */
    _readyResolved = false;

    /**
     * @private
     * @type {Map<string, MockServiceWorkerRegistration>}
     */
    _registrations = new Map();

    /** @type {MockServiceWorker | null} */
    controller = null;

    get ready() {
        return this._readyPromise;
    }

    constructor() {
        super(...arguments);

        const { promise, resolve } = Promise.withResolvers();
        /**
         * @type {Promise<MockServiceWorkerRegistration>}
         * @private
         */
        this._readyPromise = promise;
        /**
         * @type {(value: MockServiceWorkerRegistration) => void}
         * @private
         */
        this._resolveReady = resolve;
    }

    async getRegistration(scope = "/") {
        return this._registrations.get(scope);
    }

    async getRegistrations() {
        return Array.from(this._registrations.values());
    }

    /**
     * @param {string} scriptURL
     * @param {{ scope?: string }} [options]
     */
    async register(scriptURL, options = {}) {
        const scope = options.scope ?? "/";

        const registration = new MockServiceWorkerRegistration(scriptURL, scope);
        this._registrations.set(scope, registration);

        if (!this.controller) {
            this.controller = registration.active;
            this.dispatchEvent(new Event("controllerchange"));
        }

        if (!this._readyResolved) {
            this._readyResolved = true;
            this._resolveReady(registration);
        }

        return registration;
    }

    startMessages() {}
}

export class MockServiceWorkerRegistration {
    /** @type {MockServiceWorker | null} */
    installing = null;
    /** @type {MockServiceWorker | null} */
    waiting = null;

    /**
     * @param {string} scriptURL
     * @param {string} scope
     */
    constructor(scriptURL, scope) {
        /** @type {MockServiceWorker | null} */
        this.active = new MockServiceWorker(scriptURL);
        /** @type {string} */
        this.scope = scope;
    }

    async unregister() {
        return true;
    }

    async update() {}
}

export class MockStorageManager {
    async estimate() {
        return { quota: 0, usage: 0 };
    }

    /**
     * The origin private file system would otherwise persist between tests.
     */
    async getDirectory() {
        throw notAllowed("navigator.storage.getDirectory");
    }

    async persist() {
        return currentPermissions["persistent-storage"].state === "granted";
    }

    async persisted() {
        return currentPermissions["persistent-storage"].state === "granted";
    }
}

export class MockWakeLock {
    async request() {
        throw notAllowed("navigator.wakeLock.request");
    }
}

export const currentPermissions = getPermissions();

export const mockClipboard = new MockClipboard();

export const mockPermissions = new MockPermissions();

export const mockServiceWorker = new MockServiceWorkerContainer();

export const mockNavigator = createMock(navigator, {
    ...getPermissionGatedDescriptors(),
    clipboard: { value: mockClipboard },
    maxTouchPoints: { get: () => (globalThis.ontouchstart === undefined ? 0 : 1) },
    permissions: { value: mockPermissions },
    sendBeacon: { get: () => mockValues.sendBeacon },
    serviceWorker: { value: mockServiceWorker },
    userAgent: { get: () => mockValues.userAgent },
    vibrate: { get: () => mockValues.vibrate },
});

export function cleanupNavigator() {
    geolocationWatchId = 0;
    permissionStatuses.clear();
    $assign(currentPermissions, getPermissions());
    $assign(mockValues, getMockValues());
}

/**
 * @param {PermissionName} name
 * @param {PermissionState} [value]
 */
export function mockPermission(name, value) {
    ensureTest("mockPermission");
    if (!(name in currentPermissions)) {
        throw new TypeError(
            `The provided value '${name}' is not a valid enum value of type PermissionName`
        );
    }

    setPermission(name, value);
}

/**
 * @param {Navigator["sendBeacon"]} callback
 */
export function mockSendBeacon(callback) {
    ensureTest("mockSendBeacon");
    mockValues.sendBeacon = callback;
}

/**
 * @param {Platform} platform
 */
export function mockUserAgent(platform = "linux") {
    ensureTest("mockUserAgent");
    mockValues.userAgent = makeUserAgent(platform);
}

/**
 * @param {Navigator["vibrate"]} callback
 */
export function mockVibrate(callback) {
    ensureTest("mockVibrate");
    mockValues.vibrate = callback;
}
