/**
 * Converts color value from sRGB to linear RGB.
 *
 * @param {number[]} value standard rgb in [0, 255]
 * @returns {number} linear rgb
 */
function srgbToLin(value) {
    value = value / 255;
    if (value <= 0.04045) {
        return value / 12.92;
    }
    return Math.pow((value + 0.055) / 1.055, 2.4);
}

/**
 * @param {number[]} rgb [r, g, b] in [0, 255]
 * @returns {number} WCAG relative luminance
 */
export function getRelativeLuminance([r, g, b]) {
    return 0.2126 * srgbToLin(r) + 0.7152 * srgbToLin(g) + 0.0722 * srgbToLin(b);
}

/**
 * @param {number[]} fg [r, g, b]
 * @param {number[]} bg [r, g, b]
 * @returns {number} WCAG contrast ratio, from 1 to 21
 */
export function getContrastRatio(fg, bg) {
    const [hi, lo] = [getRelativeLuminance(fg), getRelativeLuminance(bg)].sort((a, b) => b - a);
    return (hi + 0.05) / (lo + 0.05);
}
