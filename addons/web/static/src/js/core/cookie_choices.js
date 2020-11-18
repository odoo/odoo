odoo.define("web.cookie_choices", function (require) {
    "use strict";

    var utils = require('web.utils');

    var ESSENTIAL = "essential";
    var ANALYTIC = "analytic";
    var MARKETING = "marketing";
    var EXTERNAL = "external";
    var COOKIE = "cookies_accepted";


    /**
     * Get cookie types accepted by the user
     *
     * @returns {Array}
     */
    function allAcceptedCookies() {
        var raw = utils.get_cookie(COOKIE) || null;
        try {
            // Cookie content comes in wrapped around double-double-quotes
            return raw.split("|");
        } catch (error) {
            return [];
        }
    }

    /**
     * Indicate if a given type of cookies is accepted by the user.
     *
     * @param {String} type Cookies type that you wonder if is accepted
     * @returns {Boolean} Indicating if the chosen cookie type is accepted
     */
    function acceptedCookies(type) {
        return type == "essential" || allAcceptedCookies().includes(type);
    }

    return {
        acceptedCookies: acceptedCookies,
        allAcceptedCookies: allAcceptedCookies,
        ANALYTIC: ANALYTIC,
        COOKIE: COOKIE,
        ESSENTIAL: ESSENTIAL,
        EXTERNAL: EXTERNAL,
        MARKETING: MARKETING,
    }

});
