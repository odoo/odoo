import { darkenColor, lightenColor } from "@web/core/colors/colors";

/**
 * Converts one color's rgb channel to how much light it actually represents (0-1).
 *
 * @param {number} channelValue 0-255
 * @returns {number}
 * @see https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 */
function toLinearLight(channelValue) {
    const sRGB = channelValue / 255;
    return sRGB <= 0.04045 ? sRGB / 12.92 : ((sRGB + 0.055) / 1.055) ** 2.4;
}

/**
 * Compute the WCAG relative luminance of a given hex color.
 *
 * @param {string} color Hexadecimal color (#rrggbb)
 * @returns {number} 0 (black) to 1 (white)
 * @see https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 */
function computeRelativeLuminance(color) {
    const r = parseInt(color.substring(1, 3), 16);
    const g = parseInt(color.substring(3, 5), 16);
    const b = parseInt(color.substring(5, 7), 16);
    return 0.2126 * toLinearLight(r) + 0.7152 * toLinearLight(g) + 0.0722 * toLinearLight(b);
}

/**
 * Scales color to the target brightness: darkens it if it's lighter, lightens otherwise.
 * Works on the sRGB values, so the result lands near the target rather than exactly on it.
 * Used for a bubble's base color so it lands at a consistent brightness regardless of the
 * configured color.
 *
 * @param {string} color
 * @param {number} targetBrightness
 * @returns {string}
 */
export function normalizeBrightness(color, targetBrightness) {
    const brightness = computeRelativeLuminance(color);
    return brightness > targetBrightness
        ? darkenColor(color, 1 - targetBrightness / brightness)
        : lightenColor(color, (targetBrightness - brightness) / (1 - brightness));
}

// Same as bootstrap ($color-contrast-dark), softer than pure black.
const CONTRAST_DARK_COLOR = "#212529";
const WHITE_BRIGHTNESS = 1;
const DARK_BRIGHTNESS = computeRelativeLuminance(CONTRAST_DARK_COLOR);
// WCAG AA is 4.5:1 for normal text, 3:1 for large text. Odoo uses 3:1
// (`$min-contrast-ratio`). Same value to match the rest of the website design. See
// https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html.
const MIN_CONTRAST_RATIO = 3;

/**
 * WCAG contrast ratio between two colors, given their brightness.
 *
 * @param {number} brightnessA
 * @param {number} brightnessB
 * @returns {number} 1 (no contrast) to 21 (black vs. white)
 * @see https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
 */
function contrastRatio(brightnessA, brightnessB) {
    return (
        (Math.max(brightnessA, brightnessB) + 0.05) / (Math.min(brightnessA, brightnessB) + 0.05)
    );
}

/**
 * Picks a readable text color for a given background color. Mirrors Bootstrap's own
 * `color-contrast`: white is used as soon as it reaches MIN_CONTRAST_RATIO, even if dark
 * text would score higher.
 *
 * @param {string} color
 */
export function getContrastColor(color) {
    const brightness = computeRelativeLuminance(color);
    if (contrastRatio(WHITE_BRIGHTNESS, brightness) >= MIN_CONTRAST_RATIO) {
        return "#FFFFFF";
    }
    if (contrastRatio(DARK_BRIGHTNESS, brightness) >= MIN_CONTRAST_RATIO) {
        return CONTRAST_DARK_COLOR;
    }
    return contrastRatio(WHITE_BRIGHTNESS, brightness) > contrastRatio(DARK_BRIGHTNESS, brightness)
        ? "#FFFFFF"
        : CONTRAST_DARK_COLOR;
}

// The maximum brightness a color can be at or under to reach MIN_CONTRAST_RATIO against a
// white background. Same formula as described in
// https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio.
export const MAX_BRIGHTNESS_FOR_WHITE_CONTRAST =
    (WHITE_BRIGHTNESS + 0.05) / MIN_CONTRAST_RATIO - 0.05;

/**
 * Caps a color's brightness: darkens it down to maxBrightness if it's lighter than that,
 * leaves it otherwise.
 *
 * @param {string} color
 * @param {number} maxBrightness
 * @returns {string}
 */
export function capBrightness(color, maxBrightness) {
    return computeRelativeLuminance(color) > maxBrightness
        ? normalizeBrightness(color, maxBrightness)
        : color;
}
