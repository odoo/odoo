import { registry } from "@web/core/registry";

/**
 * Assert that gtag consent values in `dataLayer` match the expected state.
 *
 * @param {"granted" | "denied"} expectedState
 */
function assertGtagConsent(expectedState) {
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

registry.category("web_tour.tours").add("cookie_bar_updates_gtag_consent", {
    url: "/",
    steps: () => [
        {
            content: "Accept all cookies",
            trigger: "a#cookies-consent-all",
            run: "click",
        },
        {
            content: "Ensure gtag consent is granted",
            trigger: "body",
            run: function () {
                assertGtagConsent("granted");
            },
        },
        {
            content: "Go to Cookie Policy page",
            trigger: "footer a[href='/cookie-policy']",
            run: "click",
            expectUnloadPage: true,
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
            content: "Ensure gtag consent is revoked",
            trigger: "body",
            run: function () {
                assertGtagConsent("denied");
            },
        },
    ],
});
