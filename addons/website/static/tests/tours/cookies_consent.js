/** @odoo-module **/

import { cookie } from "@web/core/browser/cookie";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("cookies_consent", {
    test: true,
    url: "/",
    steps: () => [
        {
            content: "Accept all cookies",
            trigger: "a#cookies-consent-all",
            run: "click",
        },
        {
            content: "Confirm if optional cookies are also accepted",
            trigger: "body",
            run: function () {
                const cookie_preference = JSON.parse(cookie.get("website_cookies_bar"));
                if (!cookie_preference.optional) {
                    console.error("Optional cookies must also be accepted.");
                }
            },
        },
        {
            content: "Goto Cookie Policy page",
            trigger: "footer a[href='/cookie-policy']",
            run: "click",
        },
        {
            content: "Toggle the cookie bar",
            trigger: "button.o_cookies_bar_toggle",
            run: "click",
        },
        {
            content: "Update the preference to only accept essential cookies",
            trigger: "a#cookies-consent-essential",
            run: "click",
        },
        {
            content: "Confirm if only the required cookies are accepted",
            trigger: "body",
            run: function () {
                const cookie_preference = JSON.parse(cookie.get("website_cookies_bar"));
                if (cookie_preference.optional) {
                    console.error("Optional cookies must not be accepted.");
                }
            },
        },
    ],
});
