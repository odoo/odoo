// @ts-check

/** @module @web/core/browser/cookie - Read, write, and delete browser cookies via document.cookie */

/**
 * Utils to make use of document.cookie
 * https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies
 * As recommended, storage should not be done by the cookie
 * but with localStorage/sessionStorage
 */

/** @type {number} Default cookie time-to-live in seconds (1 year). */
const COOKIE_TTL = 24 * 60 * 60 * 365;

export const cookie = {
    /** @returns {string} The raw document.cookie string. */
    get _cookieMonster() {
        return document.cookie;
    },
    /** @param {string} value - Raw cookie string to assign to document.cookie. */
    set _cookieMonster(value) {
        document.cookie = value;
    },
    /**
     * @param {string} str - Cookie name to look up.
     * @returns {string | undefined} The cookie value, or undefined if not found.
     */
    get(str) {
        const parts = this._cookieMonster.split("; ");
        for (const part of parts) {
            const [key, value] = part.split(/=(.*)/);
            if (key === str) {
                return value || "";
            }
        }
    },
    /**
     * @param {string} key - Cookie name.
     * @param {string | undefined} value - Cookie value (omit to set name-only).
     * @param {number} [ttl] - Time-to-live in seconds (defaults to 1 year).
     */
    set(key, value, ttl = COOKIE_TTL) {
        let fullCookie = [];
        if (value !== undefined) {
            fullCookie.push(`${key}=${value}`);
        }
        fullCookie = [...fullCookie, "path=/", `max-age=${Math.floor(ttl)}`];
        this._cookieMonster = fullCookie.join("; ");
    },
    /** @param {string} key - Cookie name to remove. */
    delete(key) {
        this.set(key, "kill", 0);
    },
};
