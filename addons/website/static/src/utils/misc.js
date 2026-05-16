import { cookie as cookieManager } from "@web/core/browser/cookie";

export class EventBus extends EventTarget {
    trigger(name, payload) {
        this.dispatchEvent(new CustomEvent(name, { detail: payload }));
    }
}

export function getClosestLiEls(selector) {
    return Array.from(document.querySelectorAll(selector), (el) => el.closest("li"));
}

/**
 * Unhide elements that are hidden by default and that should be visible
 * according to the snippet visibility option.
 */
export function unhideConditionalElements() {
    // Create CSS rules in a dedicated style tag according to the snippet
    // visibility option's computed ones (saved as data attributes).
    const styleEl = document.createElement("style");
    styleEl.id = "conditional_visibility";
    document.head.appendChild(styleEl);
    const conditionalEls = document.querySelectorAll('[data-visibility="conditional"]');

    const desktopMegaMenuLiEls = getClosestLiEls(
        "header#top nav:not(.o_header_mobile) .o_mega_menu_toggle"
    );
    const mobileMegaMenuLiEls = getClosestLiEls(
        "header#top nav.o_header_mobile .o_mega_menu_toggle"
    );
    for (const conditionalEl of conditionalEls) {
        // For mega menu block, add conditional visibility to the navbar link
        if (conditionalEl.parentElement.classList.contains("o_mega_menu")) {
            const desktopMegaMenuLiEl = conditionalEl.closest("li");
            const index = desktopMegaMenuLiEls.indexOf(desktopMegaMenuLiEl);
            const mobileMegaMenuLiEl = mobileMegaMenuLiEls[index];

            const visibilityId = conditionalEl.dataset.visibilityId;
            desktopMegaMenuLiEl.dataset.visibilityId = visibilityId;
            mobileMegaMenuLiEl.dataset.visibilityId = visibilityId;
        }
        const selectors = conditionalEl.dataset.visibilitySelectors;
        styleEl.sheet.insertRule(`${selectors} { display: none !important; }`);
    }

    // Now remove the classes that makes them always invisible
    for (const conditionalEl of conditionalEls) {
        conditionalEl.classList.remove("o_conditional_hidden");
    }
}

export function setUtmsHtmlDataset() {
    const htmlEl = document.documentElement;
    const cookieNamesToDataNames = {
        utm_source: "utmSource",
        utm_medium: "utmMedium",
        utm_campaign: "utmCampaign",
    };
    for (const [name, dsName] of Object.entries(cookieNamesToDataNames)) {
        const cookie = cookieManager.get(`odoo_${name}`);
        if (cookie) {
            // Remove leading and trailing " and '
            htmlEl.dataset[dsName] = cookie.replace(/(^["']|["']$)/g, "");
        }
    }
}

/**
 * Performs a basic check to make sure a link's protocol is http(s), mainly to
 * deny `javascript:` URLs.
 *
 * @param {string} link
 * @returns {URL|""} URL if the protocol is http(s), empty string otherwise
 */
export function verifyHttpsUrl(link) {
    const url = new URL(link, window.location.href);
    if (!/https?:/.test(url.protocol)) {
        return "";
    }
    return url;
}
