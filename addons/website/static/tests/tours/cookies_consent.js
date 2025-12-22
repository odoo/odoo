import { cookie } from "@web/core/browser/cookie";
import { registry } from "@web/core/registry";

/**
 * Assert that the cookie preference matches the expected state.
 *
 * @param {boolean} expectedOptional - Whether optional cookies should be
 *                                     accepted
 */
function assertOptionalCookies(expectedOptional) {
    const cookiePreference = JSON.parse(cookie.get("website_cookies_bar"));
    if (cookiePreference.optional !== expectedOptional) {
        console.error(`Optional cookies should be ${expectedOptional ? "accepted" : "rejected"}.`);
    }
}

/**
 * Assert that all consent values in `dataLayer` match the expected state.
 *
 * @param {string} expectedState - "granted" or "denied"
 */
function assertConsentInDataLayer(expectedState) {
    const lastDataLayerEntry = window.dataLayer?.at(-1);

    if (!lastDataLayerEntry || lastDataLayerEntry[0] !== "consent") {
        console.error("Cookie preference change must push a consent update to dataLayer");
        return;
    }

    const allConsentValues = Object.values(lastDataLayerEntry[2]);
    const allValuesMatch = allConsentValues.every((value) => value === expectedState);

    if (!allValuesMatch) {
        console.error(`All consent values should be '${expectedState}'`);
    }
}

registry.category("web_tour.tours").add("cookies_consent", {
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
                assertOptionalCookies(true);
                assertConsentInDataLayer("granted");
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
                assertOptionalCookies(false);
                assertConsentInDataLayer("denied");
            },
        },
    ],
});
