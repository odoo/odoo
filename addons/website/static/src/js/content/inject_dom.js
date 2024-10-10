/** @odoo-module */

import { cookie as cookieManager } from "@web/core/browser/cookie";
import { session } from "@web/session";

/**
 * Unhide elements that are hidden by default and that should be visible
 * according to the snippet visibility option.
 */
export function unhideConditionalElements() {
    // Create CSS rules in a dedicated style tag according to the snippet
    // visibility option's computed ones (saved as data attributes).
    const styleEl = document.createElement('style');
    styleEl.id = "conditional_visibility";
    document.head.appendChild(styleEl);
    const conditionalEls = document.querySelectorAll('[data-visibility="conditional"]');
    for (const conditionalEl of conditionalEls) {
        // In the case of a mega menu block, hide the mega menu link in the bar according to the same rule
        // Change the visibility for Desktop and Mobile views
        if (conditionalEl.classList.contains("s_mega_menu_odoo_menu")) {
            const megaMenuDesktopEl = conditionalEl.closest("li[role='presentation']");
            const megaMenuDesktopEls = megaMenuDesktopEl.parentElement.querySelectorAll(":scope > li[role='presentation'].dropdown");
            const index = Array.from(megaMenuDesktopEls).indexOf(megaMenuDesktopEl);
            const navDesktopEl = conditionalEl.closest("nav");
            const navMobileEl = navDesktopEl.parentElement.querySelector('.o_header_mobile');
            const megaMenuMobileEls = navMobileEl.querySelectorAll("li[role='presentation'].dropdown");
            const megaMenuMobileEl = megaMenuMobileEls[index];
            megaMenuDesktopEl.setAttribute('data-visibility-id', conditionalEl.getAttribute('data-visibility-id'));
            megaMenuMobileEl.setAttribute('data-visibility-id', conditionalEl.getAttribute('data-visibility-id'));
        }
        const selectors = conditionalEl.dataset.visibilitySelectors;
        styleEl.sheet.insertRule(`${selectors} { display: none !important; }`);
    }

    // Now remove the classes that makes them always invisible
    for (const conditionalEl of conditionalEls) {
        conditionalEl.classList.remove('o_conditional_hidden');
    }
}

export function setUtmsHtmlDataset() {
    const htmlEl = document.documentElement;
    const cookieNamesToDataNames = {
        'utm_source': 'utmSource',
        'utm_medium': 'utmMedium',
        'utm_campaign': 'utmCampaign',
    };
    for (const [name, dsName] of Object.entries(cookieNamesToDataNames)) {
        const cookie = cookieManager.get(`odoo_${name}`);
        if (cookie) {
            // Remove leading and trailing " and '
            htmlEl.dataset[dsName] = cookie.replace(/(^["']|["']$)/g, '');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Transfer cookie/session data as HTML element's attributes so that CSS
    // selectors can be based on them.
    setUtmsHtmlDataset();
    const htmlEl = document.documentElement;
    const country = session.geoip_country_code;
    if (country) {
        htmlEl.dataset.country = country;
    }
    htmlEl.dataset.logged = !session.is_website_user;

    unhideConditionalElements();
});
