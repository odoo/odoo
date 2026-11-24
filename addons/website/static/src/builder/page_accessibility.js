import { _t } from "@web/core/l10n/translation";
import { composite, getContrastRatio, parseColor } from "./color_contrast";

const OVERLAY_ATTRIBUTE = "data-page-accessibility-overlay";

const isVisible = (element) => {
    const style = element.ownerDocument.defaultView.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return (
        rect.width &&
        rect.height &&
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        parseFloat(style.opacity) !== 0
    );
};

/**
 * @returns {Object|null} the background behind the element, or null when an
 *      image or a gradient is part of it, as its contrast cannot be measured
 */
const getBackground = (element) => {
    const window = element.ownerDocument.defaultView;
    const colors = [];
    for (let current = element; current; current = current.parentElement) {
        const style = window.getComputedStyle(current);
        if (style.backgroundImage !== "none") {
            return null;
        }
        const color = parseColor(style.backgroundColor);
        if (color?.alpha) {
            colors.push(color);
        }
    }
    return colors.reverse().reduce((background, foreground) => composite(foreground, background), {
        red: 255,
        green: 255,
        blue: 255,
        alpha: 1,
    });
};

const getTextNodes = (element) =>
    [...element.childNodes].filter((node) => node.nodeType === 3 && node.textContent.trim());

/**
 * @returns {boolean|null} whether the text of the element lacks contrast, or
 *      null when its background cannot be measured
 */
const hasContrastIssue = (element) => {
    const background = getBackground(element);
    if (!background) {
        return null;
    }
    const style = element.ownerDocument.defaultView.getComputedStyle(element);
    const foreground = parseColor(style.color);
    if (!foreground) {
        return false;
    }
    const fontSize = parseFloat(style.fontSize);
    const fontWeight = parseInt(style.fontWeight, 10) || 400;
    const minimum = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700) ? 3 : 4.5;
    return getContrastRatio(composite(foreground, background), background) < minimum;
};

const addOverlay = (document, rect, label = "") => {
    const window = document.defaultView;
    const overlay = document.createElement("div");
    overlay.setAttribute(OVERLAY_ATTRIBUTE, "");
    overlay.style.cssText = `
        position: absolute;
        top: ${rect.top + window.scrollY}px;
        left: ${rect.left + window.scrollX}px;
        width: ${rect.width}px;
        height: ${rect.height}px;
        border: 2px ${label ? "dashed" : "solid"} #dc3545;
        box-shadow: 0 0 0 1px white;
        pointer-events: none;
        z-index: 2147483646;
    `;
    if (label) {
        const labelEl = document.createElement("span");
        labelEl.textContent = label;
        labelEl.style.cssText = `
            position: absolute;
            bottom: 100%;
            left: -2px;
            padding: 0 4px;
            background-color: #b02a37;
            color: white;
            font: 600 12px/1.5 system-ui, sans-serif;
            white-space: nowrap;
        `;
        overlay.appendChild(labelEl);
    }
    document.body.appendChild(overlay);
};

const addTextNodeOverlays = (document, textNodes) => {
    for (const textNode of textNodes) {
        const range = document.createRange();
        range.selectNodeContents(textNode);
        for (const rect of range.getClientRects()) {
            if (rect.width && rect.height) {
                addOverlay(document, rect);
            }
        }
        range.detach();
    }
};

export function clearPageAccessibilityHighlights(document) {
    for (const overlay of document.querySelectorAll(`[${OVERLAY_ATTRIBUTE}]`)) {
        overlay.remove();
    }
}

/**
 * Highlights the accessibility issues of the page.
 *
 * @returns {{
 *      contrast: number,
 *      emptyHeadings: number,
 *      missingAlt: number,
 *      skippedHeadingLevels: number,
 *      unchecked: number,
 * }} the number of elements with each issue, `unchecked` being the elements
 *      whose text contrast could not be measured
 */
export function highlightPageAccessibilityIssues(document) {
    clearPageAccessibilityHighlights(document);
    const results = {
        contrast: 0,
        emptyHeadings: 0,
        missingAlt: 0,
        skippedHeadingLevels: 0,
        unchecked: 0,
    };
    const root = document.querySelector("#wrapwrap") || document.body;
    for (const element of root.querySelectorAll("*")) {
        if (element.matches("script, style, template, noscript")) {
            continue;
        }
        const textNodes = getTextNodes(element);
        if (!textNodes.length || !isVisible(element)) {
            continue;
        }
        const hasIssue = hasContrastIssue(element);
        if (hasIssue === null) {
            results.unchecked++;
        } else if (hasIssue) {
            addTextNodeOverlays(document, textNodes);
            results.contrast++;
        }
    }

    // Decorative images have an empty alt, which is valid.
    const images = root.querySelectorAll(
        "img:not([alt], [aria-hidden='true'], [role='presentation'], [role='none'])"
    );
    for (const image of images) {
        if (isVisible(image)) {
            addOverlay(document, image.getBoundingClientRect(), _t("Missing alt text"));
            results.missingAlt++;
        }
    }

    // Only the headings of the page content: the header and the footer are
    // shared by all the pages.
    let previousLevel = 0;
    for (const heading of document.querySelectorAll("main :is(h1, h2, h3, h4, h5, h6)")) {
        if (!isVisible(heading)) {
            continue;
        }
        const level = Number(heading.tagName[1]);
        if (!heading.textContent.trim() && !heading.querySelector("img[alt]:not([alt=''])")) {
            addOverlay(document, heading.getBoundingClientRect(), _t("Empty heading"));
            results.emptyHeadings++;
        } else if (previousLevel && level > previousLevel + 1) {
            addOverlay(
                document,
                heading.getBoundingClientRect(),
                _t("H%(level)s after H%(previousLevel)s", { level, previousLevel })
            );
            results.skippedHeadingLevels++;
        }
        previousLevel = level;
    }
    return results;
}
