odoo.define('web.utils.cookies', function (require) {
"use strict";

return {
    /**
     * Reads the cookie described by the given name.
     *
     * @param {string} cookieName
     * @returns {string}
     */
    get_cookie(cookieName) {
        var cookies = document.cookie ? document.cookie.split('; ') : [];
        for (var i = 0, l = cookies.length; i < l; i++) {
            var parts = cookies[i].split('=');
            var name = parts.shift();
            var cookie = parts.join('=');

            if (cookieName && cookieName === name) {
                return cookie;
            }
        }
        return "";
    },
    /**
     * Creates a cookie.
     *
     * @param {string} name the name of the cookie
     * @param {string} value the value stored in the cookie
     * @param {integer} ttl time to live of the cookie in millis. -1 to erase the cookie.
     * @param {string} type the type of the cookies ('required' as default value)
     */
    set_cookie(name, value, ttl, type = 'required') {
        ttl = ttl || 24 * 60 * 60 * 365;
        if (this.checkCookie(type, name)) {
            document.cookie = [
                `${name}=${value}`,
                'path=/',
                `max-age=${ttl}`,
                `expires=${new Date(new Date().getTime() + ttl * 1000).toGMTString()}`
            ].join(';');
        }
    },
};
});
