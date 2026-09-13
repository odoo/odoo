// @ts-check
/** @odoo-module native */

import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { session } from "@web/session";

const PAYLOAD_KEY = "webclient_menus";
const VERSION_KEY = "webclient_menus_version";
const HASH_KEY = "webclient_menus_hash";
const CURRENT_APP_KEY = "menu_id";

function cacheOwner() {
    return [session.db, user.userId];
}

/** @returns {string | undefined} */
function cacheVersion() {
    return session.menus_cache_version;
}

/** @param {string} key */
function removeKey(key) {
    try {
        browser.localStorage.removeItem(key);
    } catch {}
}

function discard() {
    removeKey(PAYLOAD_KEY);
    removeKey(VERSION_KEY);
    removeKey(HASH_KEY);
}

/** @param {string} raw */
function parsePayload(raw) {
    try {
        const payload = JSON.parse(raw);
        const menus =
            payload && Object.hasOwn(payload, "cacheOwner") ? payload.menus : payload;
        if (
            !menus ||
            typeof menus !== "object" ||
            Array.isArray(menus) ||
            !Array.isArray(menus.root?.children) ||
            !Object.values(menus).every(
                (menu) =>
                    menu &&
                    typeof menu === "object" &&
                    !Array.isArray(menu) &&
                    (menu.children === undefined || Array.isArray(menu.children)),
            )
        ) {
            throw new Error("Invalid menu tree");
        }
        return payload;
    } catch {
        console.warn(
            "Corrupt webclient_menus in localStorage; discarding the cached copy",
        );
        discard();
        return null;
    }
}

export const menuStorage = {
    /** @returns {{ menus: Object | null, raw: string | null, hash: string | undefined }} */
    read() {
        let raw, storedVersion, hash;
        try {
            raw = browser.localStorage.getItem(PAYLOAD_KEY);
            storedVersion = browser.localStorage.getItem(VERSION_KEY);
            hash = browser.localStorage.getItem(HASH_KEY) || undefined;
        } catch {
            return { menus: null, raw: null, hash: undefined };
        }
        if (!raw) {
            return { menus: null, raw: null, hash: undefined };
        }
        const payload = parsePayload(raw);
        if (!payload) {
            return { menus: null, raw: null, hash: undefined };
        }
        let menus = payload;
        if (payload && Object.hasOwn(payload, "cacheOwner")) {
            if (JSON.stringify(payload.cacheOwner) !== JSON.stringify(cacheOwner())) {
                return { menus: null, raw: null, hash: undefined };
            }
            menus = payload.menus;
            raw = JSON.stringify(menus);
        } else if (storedVersion !== cacheVersion()) {
            // Legacy copies are safe only when their full server version matches.
            return { menus: null, raw: null, hash: undefined };
        }
        if (storedVersion !== cacheVersion()) {
            return { menus: null, raw, hash };
        }
        return { menus, raw, hash };
    },

    /**
     * @param {string} raw
     * @returns {Object | null}
     */
    parse(raw) {
        const payload = parsePayload(raw);
        return payload && Object.hasOwn(payload, "cacheOwner")
            ? payload.menus
            : payload;
    },

    /**
     * @param {Object} menus
     * @param {string} [hash]
     */
    write(menus, hash) {
        const version = cacheVersion();
        if (!version) {
            return;
        }
        try {
            browser.localStorage.setItem(
                PAYLOAD_KEY,
                JSON.stringify({ cacheOwner: cacheOwner(), menus }),
            );
            if (hash) {
                browser.localStorage.setItem(HASH_KEY, hash);
            } else if (browser.localStorage.getItem(HASH_KEY) !== null) {
                browser.localStorage.removeItem(HASH_KEY);
            }
            browser.localStorage.setItem(VERSION_KEY, version);
        } catch (error) {
            console.error("Error while storing menus in localStorage", error);
            removeKey(VERSION_KEY);
        }
    },

    /** @returns {number} */
    readCurrentApp() {
        try {
            return Number(browser.sessionStorage.getItem(CURRENT_APP_KEY)) || 0;
        } catch {
            return 0;
        }
    },

    /** @param {number|string} appId */
    writeCurrentApp(appId) {
        try {
            browser.sessionStorage.setItem(CURRENT_APP_KEY, String(appId));
        } catch {}
    },
};
