/** @odoo-module */
/* eslint-disable no-restricted-syntax */

import { createMock, makePublicListeners } from "../hoot_utils";

/**
 * @typedef {"android" | "ios" | "linux" | "mac" | "windows"} Platform
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    EventTarget,
    navigator,
    Object: { assign: $assign },
    Set,
    TypeError,
} = globalThis;
const { userAgent: $userAgent } = navigator;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const getUserAgentBrowser = () => {
    if (/Firefox/i.test($userAgent)) {
        return "Gecko/20100101 Firefox/1000.0"; // Firefox
    }
    if (/Chrome/i.test($userAgent)) {
        return "AppleWebKit/1000.00 (KHTML, like Gecko) Chrome/1000.00 Safari/1000.00"; // Chrome
    }
    if (/Safari/i.test($userAgent)) {
        return "AppleWebKit/1000.00 (KHTML, like Gecko) Version/1000.00 Safari/1000.00"; // Safari
    }
};

/**
 * @returns {Record<PermissionName, { name: string; state: PermissionState }>}
 */
const getPermissions = () => ({
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
});

/**
 * @param {Platform} platform
 */
const makeUserAgent = (platform) => {
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
};

/** @type {Set<MockPermissionStatus>} */
const permissionStatuses = new Set();
const userAgentBrowser = getUserAgentBrowser();
let currentUserAgent = makeUserAgent("linux");
let currentSendBeacon = () => {};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockClipboard {
    /** @type {unknown} */
    #value = null;

    async read() {
        return this.readSync();
    }

    async readText() {
        return this.readTextSync();
    }

    async write(value) {
        return this.writeSync(value);
    }

    async writeText(value) {
        return this.writeTextSync(value);
    }

    // Methods below are not part of the Clipboard API but are useful to make
    // test events synchronous.

    /**
     * @returns {unknown}
     */
    readSync() {
        return this.#value;
    }

    /**
     * @returns {string}
     */
    readTextSync() {
        return String(this.#value ?? "");
    }

    /**
     * @param {unknown} value
     */
    writeSync(value) {
        this.#value = value;
    }

    /**
     * @param {string} value
     */
    writeTextSync(value) {
        this.#value = String(value ?? "");
    }
}

export class MockPermissions {
    /**
     * @param {PermissionDescriptor} permissionDesc
     */
    async query(permissionDesc) {
        return this.querySync(permissionDesc);
    }

    // Methods below are not part of the Permissions API but are useful to make
    // test events synchronous.

    /**
     * @param {PermissionDescriptor} permissionDesc
     */
    querySync({ name }) {
        if (!(name in currentPermissions)) {
            throw new TypeError(
                `The provided value '${name}' is not a valid enum value of type PermissionName`
            );
        }
        return new MockPermissionStatus(name);
    }
}

export class MockPermissionStatus extends EventTarget {
    /** @type {typeof currentPermissions[PermissionName]} */
    #permission;

    /**
     * @param {PermissionName} name
     * @param {PermissionState} value
     */
    constructor(name) {
        super(...arguments);

        makePublicListeners(this, ["change"]);

        this.#permission = currentPermissions[name];
    }

    get name() {
        return this.#permission.name;
    }

    get state() {
        return this.#permission.state;
    }
}

export const currentPermissions = getPermissions();

export const mockClipboard = new MockClipboard();

export const mockPermissions = new MockPermissions();

export const mockNavigator = createMock(navigator, {
    clipboard: { value: mockClipboard },
    maxTouchPoints: { get: () => 0 },
    permissions: { value: mockPermissions },
    platform: { get: () => "MacIntel" },
    sendBeacon: { value: (...args) => currentSendBeacon(...args) },
    serviceWorker: { get: () => undefined },
    userAgent: { get: () => currentUserAgent },
});

export function cleanupNavigator() {
    permissionStatuses.clear();
    $assign(currentPermissions, getPermissions());
    currentUserAgent = makeUserAgent("linux");
}

/**
 * @param {PermissionName} name
 * @param {PermissionState} [value]
 */
export function mockPermission(name, value) {
    if (!(name in currentPermissions)) {
        throw new TypeError(
            `The provided value '${name}' is not a valid enum value of type PermissionName`
        );
    }

    currentPermissions[name].state = value;

    for (const permissionStatus of permissionStatuses) {
        if (permissionStatus.name === name) {
            permissionStatus.dispatchEvent(new Event("change"));
        }
    }
}

/**
 * @param {typeof navigator.sendBeacon} callback
 */
export function mockSendBeacon(callback) {
    currentSendBeacon = callback;
}

/**
 * @param {Platform} platform
 */
export function mockUserAgent(platform = "linux") {
    currentUserAgent = makeUserAgent(platform);
}
