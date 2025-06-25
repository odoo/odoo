/**
 * Utils to make use of document.cookie
 * https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies
 * As recommended, storage should not be done by the cookie
 * but with localStorage/sessionStorage
 */

const COOKIE_TTL = 24 * 60 * 60 * 365;

export const cookie = {
    get _cookieMonster() {
        return document.cookie;
    },
    set _cookieMonster(value) {
        document.cookie = value;
    },
    get(str) {
        const parts = this._cookieMonster.split("; ");
        for (const part of parts) {
            const [key, value] = part.split(/=(.*)/);
            if (key === str) {
                return value || "";
            }
        }
    },
    set(key, value, ttl = COOKIE_TTL) {
        let fullCookie = [];
        if (value !== undefined) {
            fullCookie.push(`${key}=${value}`);
        }
        fullCookie = fullCookie.concat(["path=/", `max-age=${Math.floor(ttl)}`]);
        this._cookieMonster = fullCookie.join("; ");
    },
    delete(key) {
        this.set(key, "kill", 0);
    },
};
