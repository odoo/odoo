import { registry } from "@web/core/registry";
import {
    clickOnEditAndWaitEditMode,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

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
            trigger: ".o_cookies_bar_toggle",
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

function checkCookieBarLayout(layoutAction) {
    return [
        {
            content: "Open cookie bar options",
            trigger: "[data-label='Layout'] .dropdown-toggle",
            run: "click",
        },
        {
            content: `Select ${layoutAction} layout`,
            trigger: `[data-class-action=${layoutAction}]`,
            run: "click",
        },
        {
            content: "Check cookie policy link in cookie bar",
            trigger:
                ":iframe a.o_cookies_bar_text_policy[href='/test-cookie-policy']",
        },
    ];
}

registerWebsitePreviewTour(
    "change_cookie_policy_page",
    {
        url: "/",
    },
    () => [
        {
            content: "Check cookie policy link in footer",
            trigger: ":iframe .o_cookie_policy_link_container a[href='/test-cookie-policy']",
        },
        {
            content: "Check cookie policy link in cookie bar",
            trigger: ":iframe a.o_cookies_bar_text_policy[href='/test-cookie-policy']",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Enable cookie bar editing",
            trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
            run: "click",
        },
        ...checkCookieBarLayout("o_cookies_discrete"),
        ...checkCookieBarLayout("o_cookies_classic"),
        ...checkCookieBarLayout("o_cookies_popup"),
    ]
);
