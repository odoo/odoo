/* @odoo-module */

import { assets } from "@web/core/assets";

/**
 * This file should be used in the context of an external widget loading (e.g: live chat in a non-Odoo website)
 * It overrides the 'loadJS' method that is supposed to load additional scripts, based on a relative URL (e.g: '/web/webclient/locale/en_US')
 * As we're not in an Odoo website context, the calls will not work, and we avoid a 404 request.
 */
assets.loadJS = function (url) {
    console.log("Tried to load the following script on an external website: " + url);
};
