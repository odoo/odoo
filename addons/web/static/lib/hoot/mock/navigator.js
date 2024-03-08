/** @odoo-module */
/* eslint-disable no-restricted-syntax */

import { createMock, makePublicListeners } from "../hoot_utils";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { EventTarget, navigator, Set, TypeError } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const DEFAULT_USER_AGENT =
    "Mozilla/1000.0 (X11; Linux x86_64) AppleWebKit/1000.00 (KHTML, like Gecko) Chrome/1000.0.0.0 Safari/1000.00";

/** @type {Set<MockPermissionStatus>} */
const permissionStatuses = new Set();
let currentUserAgent = DEFAULT_USER_AGENT;

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
        if (!(name in PERMISSIONS)) {
            throw new TypeError(
                `The provided value '${name}' is not a valid enum value of type PermissionName`
            );
        }
        return new MockPermissionStatus(name);
    }
}

export class MockPermissionStatus extends EventTarget {
    /** @type {typeof PERMISSIONS[PermissionName]} */
    #permission;

    /**
     * @param {PermissionName} name
     * @param {PermissionState} value
     */
    constructor(name) {
        super(...arguments);

        makePublicListeners(this, ["change"]);

        this.#permission = PERMISSIONS[name];
    }

    get name() {
        return this.#permission.name;
    }

    get state() {
        return this.#permission.state;
    }
}

export const mockClipboard = new MockClipboard();

export const mockPermissions = new MockPermissions();

export const mockNavigator = createMock(navigator, {
    clipboard: { value: mockClipboard },
    permissions: { value: mockPermissions },
    userAgent: { get: () => currentUserAgent },
    serviceWorker: { get: () => undefined },
    platform: { get: () => "MacIntel" },
    maxTouchPoints: { get: () => 0 },
});

/** @type {Record<PermissionName, { name: string; state: PermissionState }>} */
export const PERMISSIONS = {
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
let OG_PERMISSIONS = JSON.parse(JSON.stringify(PERMISSIONS));

export function cleanupNavigator() {
    permissionStatuses.clear();
    Object.assign(PERMISSIONS, OG_PERMISSIONS);
    OG_PERMISSIONS = JSON.parse(JSON.stringify(PERMISSIONS));
    currentUserAgent = DEFAULT_USER_AGENT;
}

/**
 * @param {PermissionName} name
 * @param {PermissionState} [value]
 */
export function mockPermission(name, value) {
    if (!(name in PERMISSIONS)) {
        throw new TypeError(
            `The provided value '${name}' is not a valid enum value of type PermissionName`
        );
    }

    PERMISSIONS[name].state = value;

    for (const permissionStatus of permissionStatuses) {
        if (permissionStatus.name === name) {
            permissionStatus.dispatchEvent(new Event("change"));
        }
    }
}

/**
 * @param {string} userAgent
 */
export function mockUserAgent(userAgent) {
    currentUserAgent = userAgent;
}
