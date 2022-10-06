/** @odoo-module **/

import { registry } from "../registry";

/**
 * Service to make use of document.cookie
 * https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies
 * As recommended, storage should not be done by the cookie
 * but with localStorage/sessionStorage
 */

const COOKIE_TTL = 24 * 60 * 60 * 365;

function parseCookieString(str) {
    const cookie = {};
    const parts = str.split("; ");
    for (const part of parts) {
        const [key, value] = part.split("=");
        cookie[key] = value || "";
    }
    return cookie;
}

function cookieToString(key, value, ttl = COOKIE_TTL) {
    let fullCookie = [];
    if (value !== undefined) {
        fullCookie.push(`${key}=${value}`);
    }
    fullCookie = fullCookie.concat(["path=/", `max-age=${ttl}`]);
    return fullCookie.join(";");
}

function makeCookieService() {
    function getCurrent() {
        return parseCookieString(document.cookie);
    }
    let cookie = getCurrent();
    function setCookie(key, value, ttl) {
        // TODO When this will be used from website pages, recover the
        // optional cookie mechanism.
        document.cookie = cookieToString(key, value, ttl);
        cookie = getCurrent();
    }
    return {
        get current() {
            return cookie;
        },
        setCookie,
        deleteCookie(key) {
            setCookie(key, "kill", 0);
        },
    };
}

export const cookieService = {
    start() {
        return makeCookieService();
    },
};

registry.category("services").add("cookie", cookieService);
