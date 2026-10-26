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
 * Converts a hex color to OKLCH: lightness (0-1) and chroma as the eye sees them, and the
 * hue angle (radians). Two colors with the same lightness look equally light, which is
 * not true of RGB or HSL.
 *
 * @param {string} color Hexadecimal color (#rrggbb)
 * @returns {{ l: number, c: number, h: number }}
 * @see https://bottosson.github.io/posts/oklab/
 */
function toOklch(color) {
    const [r, g, b] = [1, 3, 5].map((i) => toLinearLight(parseInt(color.substring(i, i + 2), 16)));
    const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    const okA = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
    const okB = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
    return {
        l: 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
        c: Math.hypot(okA, okB),
        h: Math.atan2(okB, okA),
    };
}

/**
 * Converts OKLCH back to a hex color. Channels out of the sRGB range are clipped.
 *
 * @param {{ l: number, c: number, h: number }} oklch
 * @returns {string}
 */
function fromOklch({ l: lightness, c, h }) {
    const okA = c * Math.cos(h);
    const okB = c * Math.sin(h);
    const l = (lightness + 0.3963377774 * okA + 0.2158037573 * okB) ** 3;
    const m = (lightness - 0.1055613458 * okA - 0.0638541728 * okB) ** 3;
    const s = (lightness - 0.0894841775 * okA - 1.291485548 * okB) ** 3;
    const linear = [
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
    ];
    return (
        "#" +
        linear
            .map((value) => {
                value = Math.min(1, Math.max(0, value));
                const sRGB = value <= 0.0031308 ? 12.92 * value : 1.055 * value ** (1 / 2.4) - 0.055;
                return Math.round(sRGB * 255)
                    .toString(16)
                    .padStart(2, "0");
            })
            .join("")
    );
}

/**
 * Caps a color's brightness: darkens it down to maxBrightness if it's lighter than that,
 * leaves it otherwise. Only the lightness changes, so the result keeps the color's hue.
 *
 * @param {string} color
 * @param {number} maxBrightness
 * @returns {string}
 */
export function capBrightness(color, maxBrightness) {
    if (computeRelativeLuminance(color) <= maxBrightness) {
        return color;
    }
    const oklch = toOklch(color);
    let [low, high] = [0, oklch.l];
    let capped = fromOklch({ ...oklch, l: low });
    for (let i = 0; i < 20; i++) {
        const middle = (low + high) / 2;
        const candidate = fromOklch({ ...oklch, l: middle });
        if (computeRelativeLuminance(candidate) <= maxBrightness) {
            [low, capped] = [middle, candidate];
        } else {
            high = middle;
        }
    }
    return capped;
}

/**
 * Background and border of a message bubble in the hue of the given color, at a fixed
 * lightness. Each role uses its own lightness, so the bubbles stay apart even when both
 * colors are the same. The chroma is capped to keep the bubbles pastel and the text
 * readable.
 *
 * @param {string} color
 * @param {number} lightness OKLCH lightness of the background (0-1)
 * @param {number} maxChroma
 * @returns {{ background: string, border: string }}
 */
export function getBubbleColors(color, lightness, maxChroma) {
    const { c, h } = toOklch(color);
    return {
        background: fromOklch({ l: lightness, c: Math.min(c, maxChroma), h }),
        border: fromOklch({ l: lightness - 0.08, c: Math.min(c, maxChroma * 1.5), h }),
    };
}
