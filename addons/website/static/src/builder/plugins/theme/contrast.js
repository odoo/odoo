import { convertCSSColorToRgba, getContrastRatio } from "@web/core/utils/colors";

const WHITE = [255, 255, 255];

// Parallax images, background videos and filters shouldn't be taken into account.
const BACKGROUND_LAYER_SELECTOR =
    ":scope > .s_parallax_bg_wrap, :scope > .o_bg_video_container, :scope > .o_we_bg_filter";

function parseColor(value) {
    const rgba = convertCSSColorToRgba(value);
    return rgba && [rgba.red, rgba.green, rgba.blue, rgba.opacity / 100];
}

function composite([r, g, b, a], bottom) {
    return [r, g, b].map((channel, i) => channel * a + bottom[i] * (1 - a));
}

/**
 * Resolve the opaque color painted behind `el`, or null when an image or a
 * gradient (or an unparsable color) lies in between and makes it unknowable.
 *
 * @param {HTMLElement} el
 * @returns {number[] | null} [r, g, b]
 */
function getEffectiveBackground(el) {
    if (!el) {
        return WHITE;
    }
    const style = el.ownerDocument.defaultView.getComputedStyle(el);
    const color = parseColor(style.backgroundColor);
    if (!color || style.backgroundImage !== "none" || el.querySelector(BACKGROUND_LAYER_SELECTOR)) {
        return null;
    }
    if (color[3] >= 1) {
        return color;
    }
    const below = getEffectiveBackground(el.parentElement);
    return below && composite(color, below);
}

function hasOwnText(el) {
    return [...el.childNodes].some(
        (node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim()
    );
}

function isLargeText(style) {
    const size = parseFloat(style.fontSize);
    return size >= 24 || (size >= 18.66 && parseInt(style.fontWeight) >= 700);
}

/**
 * Find the visible elements of `rootEl` whose own text fails the WCAG 2.x AA
 * contrast minimum against its background. Text over background images or
 * gradients is skipped, as its contrast cannot be computed.
 *
 * @param {HTMLElement} rootEl
 * @returns {{ el: HTMLElement, ratio: number, threshold: number }[]} in
 *   document order
 */
export function findLowContrastElements(rootEl) {
    const doc = rootEl.ownerDocument;
    const view = doc.defaultView;
    // Read the final colors, not those of running transitions (e.g. right
    // after a theme change reloaded the stylesheets).
    const noTransitionEl = doc.createElement("style");
    noTransitionEl.textContent = "* { transition: none !important; }";
    doc.head.append(noTransitionEl);
    const results = [];
    try {
        for (const el of rootEl.querySelectorAll("*")) {
            if (!hasOwnText(el) || !el.getClientRects().length) {
                continue;
            }
            const style = view.getComputedStyle(el);
            const color = parseColor(style.color);
            const background = getEffectiveBackground(el);
            if (!color || !background) {
                continue;
            }
            const ratio = getContrastRatio(composite(color, background), background);
            const threshold = isLargeText(style) ? 3 : 4.5;
            if (ratio < threshold) {
                results.push({ el, ratio, threshold });
            }
        }
    } finally {
        noTransitionEl.remove();
    }
    return results;
}
