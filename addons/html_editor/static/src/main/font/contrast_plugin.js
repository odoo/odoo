import { Plugin } from "@html_editor/plugin";
import { convertCSSColorToRgba, convertRgbToHsl, convertHslToRgb } from "@web/core/utils/colors";
import { hasColor, hasTextColorClass } from "@html_editor/utils/color";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { removeStyle } from "@html_editor/utils/dom";

export class ContrastPlugin extends Plugin {
    static id = "contrast";
    resources = {
        before_color_element_processors: this.restoreOriginalColors.bind(this),
        clean_for_save_processors: this.restoreOriginalColors.bind(this),
    };

    setup() {
        const htmlStyle = getHtmlStyle(document);
        this.defaultBg = getCSSVariableValue("o-control-panel-background-color", htmlStyle);

        this.applyContrast();
    }

    /**
     * Adjusts element colors to improve readability against background.
     */
    applyContrast() {
        const elementColorData = [];
        const adjustedColors = new Map();
        this.resolvedBackgrounds = new WeakMap();

        const walker = document.createTreeWalker(this.editable, NodeFilter.SHOW_ELEMENT, {
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
                bg
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
                    element.style.setProperty("color", adjustedColor, "important");
                } else {
                    element.style.color = adjustedColor;
                }
            }
        }
    }

    /**
     * Computes the resolved background color for an element by
     * blending its background with the nearest ancestor background
     * or the theme background.
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
            hasColor(el, "backgroundColor")
        );

        const baseBg = this.resolvedBackgrounds.get(parentBgEl) || this.defaultBg;

        return this.blendWithBackground(
            elWithBg.style.backgroundColor || getComputedStyle(elWithBg).backgroundColor,
            baseBg
        );
    }

    /**
     * Resolves a color against a background, taking alpha transparency into account.
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

const srgbToLin = (v) =>
    v / 255 <= 0.04045 ? v / 255 / 12.92 : Math.pow((v / 255 + 0.055) / 1.055, 2.4);

const lum = ([r, g, b]) => 0.2126 * srgbToLin(r) + 0.7152 * srgbToLin(g) + 0.0722 * srgbToLin(b);

const contrast = (fg, bg) => {
    const hi = Math.max(lum(fg), lum(bg));
    const lo = Math.min(lum(fg), lum(bg));
    return (hi + 0.05) / (lo + 0.05);
};

/**
 * Adjusts color lightness to improve contrast against background.
 * Uses binary search for optimal lightness.
 *
 * @param {string} color - CSS color
 * @param {string} background - CSS background color
 * @returns {string|null} Adjusted color as rgb() or null if no change needed
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
    const { hue: h, saturation: s, lightness: l } = hsl; // h in [0, 360], s,l in [0, 100]

    // Adjust lightness toward the opposite end from the background
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
