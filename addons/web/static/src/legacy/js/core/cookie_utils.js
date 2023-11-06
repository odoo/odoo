odoo.define('web.utils.cookies', function (require) {
"use strict";

const utils = {
    /**
     * Reads the cookie described by the given name.
     *
     * @param {string} cookieName
     * @returns {string}
     */
    getCookie(cookieName) {
        var cookies = document.cookie ? document.cookie.split('; ') : [];
        for (var i = 0, l = cookies.length; i < l; i++) {
            var parts = cookies[i].split('=');
            var name = parts.shift();
            var cookie = parts.join('=');

            if (cookieName && cookieName === name) {
                if (cookie.startsWith('"')) {
                    if (cookie.includes('\\')){
                        // see werkzeug _cookie_quote
                        throw new Error(
                            `Cookie value contains unknown characters ${cookie}`
                        )
                    }
                    cookie = cookie.slice(1, -1);
                }
                return cookie;
            }
        }
        return "";
    },
    /**
     * Check if cookie can be written.
     *
     * @param {String} type the type of the cookie
     * @returns {boolean}
     */
    isAllowedCookie(type) {
        return true;
    },
    /**
     * Creates a cookie.
     *
     * @param {string} name the name of the cookie
     * @param {string} value the value stored in the cookie
     * @param {integer} ttl time to live of the cookie in millis. -1 to erase the cookie.
     * @param {string} type the type of the cookies ('required' as default value)
     */
    setCookie(name, value, ttl = 31536000, type = 'required') {
        ttl = utils.isAllowedCookie(type) ? ttl || 24 * 60 * 60 * 365 : -1;
        document.cookie = [
            `${name}=${value}`,
            'path=/',
            `max-age=${ttl}`,
            `expires=${new Date(new Date().getTime() + ttl * 1000).toGMTString()}`,
        ].join(';');
    },
    /**
     * Deletes a cookie.
     *
     * @param {string} name the name of the cookie
     */
    deleteCookie(name) {
        document.cookie = [
            `${name}=`,
            'path=/',
            `max-age=-1`,
            `expires=${new Date(new Date().getTime() - 1000).toGMTString()}`,
        ].join(';');
    },
};
return utils;
});
