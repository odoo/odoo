// ============================================================================
// CONSTANTS & CONFIGURATION
// ============================================================================

import { signal } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export const DEFAULT_WEBSITE_NAME = _t("My Website");
export const MAIN_LOGO_TARGET = "header";
export const LOGO_OPTION_CONFIG = {
    header: {
        selector: ".navbar-brand.logo span img",
        label: _t("Header Logo"),
    },
    footer: {
        selector: ".o_footer_logo img",
        label: _t("Footer Logo"),
    },
};
export const LOGO_TARGETS_NAME = Object.keys(LOGO_OPTION_CONFIG);
// ============================================================================
// GETTERS
// ============================================================================

/**
 * Retrieves the logo image elements based on the requested targets.
 *
 * @param {Document|HTMLElement} root
 * @param {Array<string>} targets Ex: ["header", "footer"]
 * @returns {Array<HTMLImageElement>}
 */
export function getLogoElements(root, targets = LOGO_TARGETS_NAME) {
    const foundLogos = [];
    for (const target of targets) {
        const selector = LOGO_OPTION_CONFIG[target]?.selector;
        if (!selector) {
            continue;
        }

        // Use querySelectorAll to find all matching elements (in case of duplicates)
        const imgElements = root.querySelectorAll(selector);
        foundLogos.push(...imgElements);
    }

    return foundLogos;
}

export function getInitialLogoState(root) {
    return Object.fromEntries(
        LOGO_TARGETS_NAME.map((target) => {
            const selector = LOGO_OPTION_CONFIG[target].selector;
            const elements = selector ? root.querySelectorAll(selector) : [];
            const initialUrl = elements[0]?.src || null;

            return [
                target,
                {
                    hasChange: signal(false),
                    initialUrlValue: initialUrl,
                },
            ];
        })
    );
}

// ============================================================================
// OBSERVERS
// ============================================================================

/**
 * Sets up a MutationObserver to reactively track external logo changes.
 *
 * @param {Document|HTMLElement} root The document or root element to observe.
 * @param {Object} logosState The reactive OWL state tracking the logos.
 * @returns {MutationObserver} The active observer instance.
 */
export function observeLogoChanges(root, logosState) {
    const observer = new MutationObserver(() => {
        for (const target of LOGO_TARGETS_NAME) {
            const currentElement = getLogoElements(root, [target])[0];
            const currentSrc = currentElement ? currentElement.getAttribute("src") : null;
            const isChanged = Boolean(!logosState[target]?.initialUrlValue?.includes(currentSrc));
            if (logosState[target].hasChange() !== isChanged) {
                logosState[target].hasChange.set(isChanged);
            }
        }
    });
    observer.observe(root, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["src"],
    });

    return observer;
}

// ============================================================================
// SETTERS
// ============================================================================

/**
 * Updates the logos based on the requested targets.
 *
 * @param {Document|HTMLElement} document
 * @param {string} url
 * @param {Array<string>} targets Ex: ["header", "footer"]
 */
export function applyLogo(document, url, targets = LOGO_TARGETS_NAME) {
    if (!url) {
        return;
    }
    const logoElements = getLogoElements(document, targets);
    logoElements.forEach((imgElement) => {
        imgElement.src = url;
    });
}

/**
 * Orchestrates the DOM and Title Service updates for the website name.
 *
 * @param {HTMLElement|Document} rootElement The root element to update.
 * @param {Object} titleService The Odoo title service.
 * @param {string} name The new website name.
 * @param {string} previousName The previous website name.
 * @returns {Array<Function>} Array of rollback functions to reverse DOM and Title Service changes.
 */
export function applyWebsiteName(titleService, name, previousName) {
    const parts = titleService.getParts() || {};
    const updatedParts = {};
    const originalPartsToRestore = {};

    for (const [key, value] of Object.entries(parts)) {
        if (typeof value === "string" && value.includes(previousName)) {
            updatedParts[key] = replaceLastOccurrence(value, previousName, name);
            originalPartsToRestore[key] = value;
        }
    }

    const rollbacks = [];
    if (Object.keys(updatedParts).length > 0) {
        titleService.setParts(updatedParts);
        rollbacks.push(() => {
            titleService.setParts(originalPartsToRestore);
        });
    }
    return rollbacks;
}

/**
 * Updates the favicon in the top window document.
 *
 * @param {string|null} url The URL of the new favicon, or null to remove it.
 */
export function applyFavicon(url, doc = window.top.document) {
    doc.head.querySelectorAll("link[rel*='icon']").forEach((link) => (link.href = url || "data:,"));
}

// ============================================================================
// UTILS
// ============================================================================

/**
 * Replaces the last occurrence of a substring within a string.
 *
 * @param {string} str The original string.
 * @param {string} search The substring to search for.
 * @param {string} replacement The substring to replace it with.
 * @returns {string} The modified string.
 */
export function replaceLastOccurrence(str, search, replacement) {
    const index = str.lastIndexOf(search);
    if (index === -1) {
        return str;
    }
    return str.slice(0, index) + replacement + str.slice(index + search.length);
}

/**
 * Builds a media URL for a website asset (logo/favicon).
 *
 * @param {number} websiteId The ID of the website.
 * @param {string} field The field name (e.g., 'logo', 'favicon').
 * @param {boolean} hasMedia Whether the media exists.
 * @param {number} token The cache-busting token.
 * @returns {string|null} The formatted URL, or null if no media exists.
 */
export function buildMediaUrl(websiteId, field, hasMedia) {
    if (!hasMedia) {
        return null;
    }
    return `/web/image/website/${websiteId}/${field}`;
}
