/** @odoo-module **/

import { parseJSON } from "@website/js/utils";
import { cookie } from "@web/core/browser/cookie";
import { patch } from "@web/core/utils/patch";

patch(cookie, {
    isAllowedCookie(type) {
        if (type === "optional") {
            if (!document.getElementById("cookies-consent-essential")) {
                // Cookies bar is disabled on this website.
                return true;
            }
            const consents = parseJSON(cookie.get("website_cookies_bar") || "{}");

            // pre-16.0 compatibility, `website_cookies_bar` was `"true"`.
            // In that case we delete that cookie and let the user choose again.
            // A malformed cookie is handled the same way.
            if (!consents || typeof consents !== "object") {
                cookie.delete("website_cookies_bar");
                return false;
            }

            if ("optional" in consents) {
                return consents["optional"];
            }
            return false;
        }
        return true;
    },
    set(key, value, ttl, type = "required") {
        super.set(key, value, this.isAllowedCookie(type) ? ttl : 0);
    },
});
