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
        // For mega menu block, add conditional visibility to the navbar link
        if (conditionalEl.parentElement.classList.contains("o_mega_menu")) {
            const desktopMegaMenuToggleEl = conditionalEl.closest("li[role='presentation']");
            const desktopMegaMenuToggleEls = desktopMegaMenuToggleEl.parentElement.querySelectorAll(
                `li[role='presentation'].dropdown`
            );
            const index = Array.from(desktopMegaMenuToggleEls).indexOf(desktopMegaMenuToggleEl);
            const mobileMegaMenuToggleEl = document.querySelectorAll(
                `header nav.o_header_mobile li[role='presentation'].dropdown`
            )[index];

            const visibilityId = conditionalEl.getAttribute("data-visibility-id");
            desktopMegaMenuToggleEl.setAttribute("data-visibility-id", visibilityId);
            mobileMegaMenuToggleEl.setAttribute("data-visibility-id", visibilityId);
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

    document
        .querySelectorAll(".o_mega_menu section.o_snippet_desktop_invisible")
        .forEach((el) => el.closest("li").classList.add("d-none"));

    // Since Mega Menus are located in the desktop header at first, we need
    // to get the indices of the mega menu elements to hide the correct one
    // in mobile
    const megaMenuSectionEls = document.querySelectorAll(".o_mega_menu section");
    const noMobileMegaMenuEls = document.querySelectorAll(
        ".o_mega_menu section.o_snippet_mobile_invisible"
    );
    if (noMobileMegaMenuEls.length != 0) {
        const mobileMegaMenuToggleEls = document.querySelectorAll(
            `header nav.o_header_mobile li[role='presentation'].dropdown`
        );
        for (const megaMenuEl of noMobileMegaMenuEls) {
            const index = Array.from(megaMenuSectionEls).indexOf(megaMenuEl);
            mobileMegaMenuToggleEls[index].classList.add("d-none");
        }
    }

    unhideConditionalElements();
});
