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

<<<<<<< f185efc07caae71d3eb0be13bdde7c0c4b733439
registry.category("web_tour.tours").add("cookie_bar_updates_gtag_consent", {
||||||| 6c2294507f22a3380bedccb229f42a90bd3658d8
registry.category("web_tour.tours").add("cookies_consent", {
=======
/**
 * Assert that the Google tag blocked before consent has been restored.
 */
function assertGoogleTagLoaded() {
    if (!document.querySelector("script[src^='https://www.googletagmanager.com/gtag/js']")) {
        console.error("The Google tag should be loaded once optional cookies are accepted");
    }
}

registry.category("web_tour.tours").add("cookies_consent", {
>>>>>>> d1d081c83ed4effb3f755ef52e104be73a51da80
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
<<<<<<< f185efc07caae71d3eb0be13bdde7c0c4b733439
                assertGtagConsent("granted");
||||||| 6c2294507f22a3380bedccb229f42a90bd3658d8
                assertOptionalCookies(true);
                assertConsentInDataLayer("granted");
=======
                assertOptionalCookies(true);
                assertConsentInDataLayer("granted");
                assertGoogleTagLoaded();
>>>>>>> d1d081c83ed4effb3f755ef52e104be73a51da80
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
