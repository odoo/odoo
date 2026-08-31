/** @odoo-module native */
import { Plugin } from "@html_editor/plugin";
import { hasColor, hasTextColorClass } from "@html_editor/utils/color";
import { removeStyle } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import {
    convertCSSColorToRgba,
    convertHslToRgb,
    convertRgbToHsl,
} from "@web/core/utils/format/colors";

/**
 * Text saved with a colour that is nearly the colour of the page behind it is
 * unreadable in the editor. This plugin darkens or lightens such colours just
 * enough to be legible, keeps the author's colour in `data-original-color`, and
 * puts it back before the content is saved -- so what is stored is always what
 * the author chose.
 */
export class ContrastPlugin extends Plugin {
    static id = "contrast";
    resources = {
        before_color_element_processors: this.restoreOriginalColors.bind(this),
        clean_for_save_handlers: ({ root }) => this.restoreOriginalColors(root),
    };

    setup() {
        const htmlStyle = getHtmlStyle(this.document);
        // Our fork publishes the page background through the token system, so
        // that is what the editor reads.
        this.defaultBg =
            toRgbColor(getCSSVariableValue("o-bg-view", htmlStyle), this.document) ||
            "rgb(255, 255, 255)";

        this.applyContrast();
    }

    /**
     * Adjusts element colors to improve readability against background.
     */
    applyContrast() {
        const elementColorData = [];
        const adjustedColors = new Map();
        this.resolvedBackgrounds = new WeakMap();

        const walker = this.document.createTreeWalker(this.editable, NodeFilter.SHOW_ELEMENT, {
            acceptNode(node) {
                return hasColor(node, "color") || hasColor(node, "backgroundColor")
                    ? NodeFilter.FILTER_ACCEPT
                    : NodeFilter.FILTER_SKIP;
            },
        });

        while (walker.nextNode()) {
            const element = walker.currentNode;
            const bg = this.getEffectiveBackground(element);
            const color = this.blendWithBackground(
                element.style.color || getComputedStyle(element).color,
                bg,
            );
            const hasColorClass = hasTextColorClass(element, "color");

            elementColorData.push({ element, color, bg, hasColorClass });
            this.resolvedBackgrounds.set(element, bg);
        }

        for (const { element, color, bg, hasColorClass } of elementColorData) {
            const key = `${color}|${bg}`;
            let adjustedColor;

            if (adjustedColors.has(key)) {
                adjustedColor = adjustedColors.get(key);
            } else {
                adjustedColor = adjustColorContrast(color, bg);
                adjustedColors.set(key, adjustedColor);
            }
            if (adjustedColor) {
                element.dataset.originalColor = element.style.color || "";
                if (hasColorClass) {
                    // The class still carries the author's colour, so the
                    // adjustment has to outrank it.
                    element.style.setProperty("color", adjustedColor, "important");
                } else {
                    element.style.color = adjustedColor;
                }
            }
        }
    }

    /**
     * Computes the resolved background color for an element by blending its
     * background with the nearest ancestor background or the theme background.
     *
     * @param {HTMLElement} element
     * @returns {string} background color as rgb() or hex string
     */
    getEffectiveBackground(element) {
        const elWithBg = closestElement(element, (el) => hasColor(el, "backgroundColor"));
        if (!elWithBg) {
            return this.defaultBg;
        }

        const parentBgEl = closestElement(elWithBg.parentElement, (el) =>
            hasColor(el, "backgroundColor"),
        );

        const baseBg = this.resolvedBackgrounds.get(parentBgEl) || this.defaultBg;

        return this.blendWithBackground(
            elWithBg.style.backgroundColor || getComputedStyle(elWithBg).backgroundColor,
            baseBg,
        );
    }

    /**
     * Resolves a color against a background, taking alpha transparency into
     * account.
     *
     * @param {string} cssColor - CSS color string to resolve
     * @param {string} bgColor - Background color to blend against (as rgb())
     * @returns {string} Resolved color as rgb()
     */
    blendWithBackground(cssColor, bgColor) {
        const parsed = convertCSSColorToRgba(cssColor);
        if (!parsed || parsed.opacity === 0) {
            return bgColor;
        }
        if (parsed.opacity === 100) {
            return `rgb(${parsed.red}, ${parsed.green}, ${parsed.blue})`;
        }

        // Blend with background for partial transparency
        const base = convertCSSColorToRgba(bgColor);
        const a = parsed.opacity / 100;
        const r = Math.round(parsed.red * a + base.red * (1 - a));
        const g = Math.round(parsed.green * a + base.green * (1 - a));
        const b = Math.round(parsed.blue * a + base.blue * (1 - a));
        return `rgb(${r}, ${g}, ${b})`;
    }

    /**
     * Restores original colors by removing contrast adjustments.
     *
     * @param {HTMLElement} element
     */
    restoreOriginalColors(element) {
        const restoreColor = (el) => {
            const original = el.dataset.originalColor;
            if (original) {
                el.style.color = original;
            } else {
                removeStyle(el, "color");
            }
            el.removeAttribute("data-original-color");
        };

        // Color change: restore the original color of the adjusted element.
        if (element.hasAttribute?.("data-original-color")) {
            restoreColor(element);
        } else {
            // Content save: restore the original colors of all adjusted elements.
            element.querySelectorAll("[data-original-color]").forEach(restoreColor);
        }
        return element;
    }
}

/**
 * `--o-bg-view` holds whatever the palette wrote into it, and ours writes the
 * keyword `white`. `convertCSSColorToRgba` reads rgb()/rgba()/hex and nothing
 * else, so the keyword would resolve to nothing and every contrast check
 * against the page background would silently do nothing. Upstream sidestepped
 * this by rewriting the SCSS literal to a hex; that file is in `web`, outside
 * this module, so the value is normalised here by the one thing that
 * understands every CSS colour notation: the document.
 *
 * @param {string} cssColor
 * @param {Document} doc
 * @returns {string} an rgb() string, or "" if the colour is not usable
 */
function toRgbColor(cssColor, doc) {
    if (!cssColor) {
        return "";
    }
    if (convertCSSColorToRgba(cssColor)) {
        return cssColor;
    }
    // `body` is not there yet when the editor lives in an iframe that is still
    // being written to.
    const host = doc.body || doc.documentElement;
    if (!host) {
        return "";
    }
    const probe = doc.createElement("span");
    probe.style.color = cssColor;
    host.append(probe);
    const rgb = getComputedStyle(probe).color;
    probe.remove();
    return convertCSSColorToRgba(rgb) ? rgb : "";
}

const srgbToLin = (v) =>
    v / 255 <= 0.04045 ? v / 255 / 12.92 : Math.pow((v / 255 + 0.055) / 1.055, 2.4);

const lum = ([r, g, b]) => 0.2126 * srgbToLin(r) + 0.7152 * srgbToLin(g) + 0.0722 * srgbToLin(b);

const contrast = (fg, bg) => {
    const hi = Math.max(lum(fg), lum(bg));
    const lo = Math.min(lum(fg), lum(bg));
    return (hi + 0.05) / (lo + 0.05);
};

/**
 * Adjusts color lightness to improve contrast against background. Uses binary
 * search for optimal lightness.
 *
 * @param {string} color - CSS color
 * @param {string} background - CSS background color
 * @returns {string|undefined} Adjusted color as rgb(), or nothing if no change
 *      is needed
 */
export function adjustColorContrast(color, background) {
    const parsedColor = convertCSSColorToRgba(color);
    if (!parsedColor) {
        return;
    }
    const parsedBg = convertCSSColorToRgba(background);
    if (!parsedBg) {
        return;
    }

    const fg = [parsedColor.red, parsedColor.green, parsedColor.blue];
    const bg = [parsedBg.red, parsedBg.green, parsedBg.blue];

    // Early exit: contrast already sufficient
    const MIN_CONTRAST = 2;
    if (contrast(fg, bg) >= MIN_CONTRAST) {
        return;
    }

    const hsl = convertRgbToHsl(fg[0], fg[1], fg[2]);
    if (!hsl) {
        return;
    }
    const { hue: h, lightness: l } = hsl; // h in [0, 360], s,l in [0, 100]
    // `convertRgbToHsl` can return a saturation a hair over 100 for a fully
    // saturated colour, and `convertHslToRgb` rejects anything above it, which
    // would silently skip the adjustment. Clamped here rather than in
    // `web/core/utils/format/colors`, which is outside this module.
    const s = Math.min(100, hsl.saturation);

    // Adjust lightness toward the opposite end from the background.
    // If the background is light, push the color darker (dir = -1).
    // If the background is dark,  push the color lighter (dir = +1).
    const dir = lum(bg) > 0.5 ? -1 : 1;
    const MAX_DELTA = 50;

    let low = 0,
        high = Math.min(MAX_DELTA, dir === -1 ? l : 100 - l), // operate in [0, 100] space
        bestL = l;
    for (let i = 0; i < 15; i++) {
        if (high - low < 0.2) {
            break;
        }

        const delta = (low + high) / 2;
        const lCandidate = l + dir * delta;
        const rgb = convertHslToRgb(h, s, lCandidate);
        if (rgb && contrast([rgb.red, rgb.green, rgb.blue], bg) >= MIN_CONTRAST) {
            bestL = lCandidate;
            high = delta;
        } else {
            low = delta;
        }
    }

    const result = convertHslToRgb(h, s, bestL);
    if (!result) {
        return;
    }
    return `rgb(${result.red}, ${result.green}, ${result.blue})`;
}
