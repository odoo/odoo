import { convertCSSColorToRgba } from "@web/core/utils/colors";
import { getContrastRatio } from "@html_editor/utils/contrast";

const WHITE = { r: 255, g: 255, b: 255 };

// Parallax images, background videos and filters shouldn't be taken into account.
const BACKGROUND_LAYER_SELECTOR =
    ":scope > .s_parallax_bg_wrap, :scope > .o_bg_video_container, :scope > .o_we_bg_filter";

function parseColor(value) {
    const rgba = convertCSSColorToRgba(value);
    return rgba && { r: rgba.red, g: rgba.green, b: rgba.blue, a: rgba.opacity / 100 };
}

function composite(top, bottom) {
    const mix = (channel) => top[channel] * top.a + bottom[channel] * (1 - top.a);
    return { r: mix("r"), g: mix("g"), b: mix("b"), a: 1 };
}

/**
 * Resolve the opaque colour painted behind `el`, or null when an image or a
 * gradient (or an unparsable colour) lies in between and makes it unknowable.
 *
 * @param {HTMLElement} el
 * @returns {{ r: number, g: number, b: number, a: 1 } | null}
 */
export function getEffectiveBackground(el) {
    const view = el.ownerDocument.defaultView;
    const layers = [];
    let current = el;
    let background = null;
    while (current && !background) {
        const style = view.getComputedStyle(current);
        if (style.backgroundImage !== "none" || current.querySelector(BACKGROUND_LAYER_SELECTOR)) {
            return null;
        }
        const color = parseColor(style.backgroundColor);
        if (!color) {
            return null;
        }
        if (color.a >= 1) {
            background = color;
        } else if (color.a > 0) {
            layers.push(color);
        }
        current = current.parentElement;
    }
    return layers.reduceRight((below, layer) => composite(layer, below), background ?? WHITE);
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
 * @returns {{
 *   el: HTMLElement,
 *   color: { r: number, g: number, b: number },
 *   background: { r: number, g: number, b: number },
 *   ratio: number,
 *   required: number,
 * }[]} in document order
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
        const textColor = composite(color, background);
        const ratio = getContrastRatio(
            [textColor.r, textColor.g, textColor.b],
            [background.r, background.g, background.b]
        );
        const required = isLargeText(style) ? 3 : 4.5;
        if (ratio < required) {
            results.push({ el, color: textColor, background, ratio, required });
        }
    }
    noTransitionEl.remove();
    return results;
}
