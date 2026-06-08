/**
 * Adds opacity to the gradient
 *
 * @static
 * @param {string} gradient - css gradient string
 * @param {number} opacity - [0, 1] {float}
 * @returns {string} - gradient string with opacity
 */
export function applyOpacityToGradient(gradient, opacity = 100) {
    if (opacity === 100) {
        return gradient;
    }
    return gradient.replace(/rgb\(([^)]+)\)/g, `rgba($1, ${opacity / 100.0})`);
}
/**
 * Converts RGB color components to HSL components.
 *
 * @static
 * @param {integer} r - [0, 255]
 * @param {integer} g - [0, 255]
 * @param {integer} b - [0, 255]
 * @returns {Object|false}
 *          - hue [0, 360[ (float)
 *          - saturation [0, 100] (float)
 *          - lightness [0, 100] (float)
 */
export function convertRgbToHsl(r, g, b) {
    if (
        typeof r !== "number" ||
        isNaN(r) ||
        r < 0 ||
        r > 255 ||
        typeof g !== "number" ||
        isNaN(g) ||
        g < 0 ||
        g > 255 ||
        typeof b !== "number" ||
        isNaN(b) ||
        b < 0 ||
        b > 255
    ) {
        return false;
    }

    var red = r / 255;
    var green = g / 255;
    var blue = b / 255;
    var maxColor = Math.max(red, green, blue);
    var minColor = Math.min(red, green, blue);
    var delta = maxColor - minColor;
    var hue = 0;
    var saturation = 0;
    var lightness = (maxColor + minColor) / 2;
    if (delta) {
        if (maxColor === red) {
            hue = (green - blue) / delta;
        }
        if (maxColor === green) {
            hue = 2 + (blue - red) / delta;
        }
        if (maxColor === blue) {
            hue = 4 + (red - green) / delta;
        }
        if (maxColor) {
            saturation = delta / (1 - Math.abs(2 * lightness - 1));
        }
    }
    hue = 60 * hue;
    return {
        hue: hue < 0 ? hue + 360 : hue,
        saturation: saturation * 100,
        lightness: lightness * 100,
    };
}
/**
 * Converts HSL color components to RGB components.
 *
 * @static
 * @param {number} h - [0, 360[ (float)
 * @param {number} s - [0, 100] (float)
 * @param {number} l - [0, 100] (float)
 * @returns {Object|false}
 *          - red [0, 255] (integer)
 *          - green [0, 255] (integer)
 *          - blue [0, 255] (integer)
 */
export function convertHslToRgb(h, s, l) {
    if (
        typeof h !== "number" ||
        isNaN(h) ||
        h < 0 ||
        h > 360 ||
        typeof s !== "number" ||
        isNaN(s) ||
        s < 0 ||
        s > 100 ||
        typeof l !== "number" ||
        isNaN(l) ||
        l < 0 ||
        l > 100
    ) {
        return false;
    }

    var huePrime = h / 60;
    var saturation = s / 100;
    var lightness = l / 100;
    var chroma = saturation * (1 - Math.abs(2 * lightness - 1));
    var secondComponent = chroma * (1 - Math.abs((huePrime % 2) - 1));
    var lightnessAdjustment = lightness - chroma / 2;
    var precision = 255;
    chroma = Math.round((chroma + lightnessAdjustment) * precision);
    secondComponent = Math.round((secondComponent + lightnessAdjustment) * precision);
    lightnessAdjustment = Math.round(lightnessAdjustment * precision);
    if (huePrime >= 0 && huePrime < 1) {
        return {
            red: chroma,
            green: secondComponent,
            blue: lightnessAdjustment,
        };
    }
    if (huePrime >= 1 && huePrime < 2) {
        return {
            red: secondComponent,
            green: chroma,
            blue: lightnessAdjustment,
        };
    }
    if (huePrime >= 2 && huePrime < 3) {
        return {
            red: lightnessAdjustment,
            green: chroma,
            blue: secondComponent,
        };
    }
    if (huePrime >= 3 && huePrime < 4) {
        return {
            red: lightnessAdjustment,
            green: secondComponent,
            blue: chroma,
        };
    }
    if (huePrime >= 4 && huePrime < 5) {
        return {
            red: secondComponent,
            green: lightnessAdjustment,
            blue: chroma,
        };
    }
    if (huePrime >= 5 && huePrime <= 6) {
        return {
            red: chroma,
            green: lightnessAdjustment,
            blue: secondComponent,
        };
    }
    return false;
}
/**
 * Converts RGBA color components to a normalized CSS color: if the opacity
 * is invalid or equal to 100, a hex color excluding opacity is returned;
 * otherwise a hex color including opacity component is returned.
 *
 * @static
 * @param {integer} r - [0, 255]
 * @param {integer} g - [0, 255]
 * @param {integer} b - [0, 255]
 * @param {float} a - [0, 100]
 * @returns {string}
 */
export function convertRgbaToCSSColor(r, g, b, a) {
    if (
        typeof r !== "number" ||
        isNaN(r) ||
        r < 0 ||
        r > 255 ||
        typeof g !== "number" ||
        isNaN(g) ||
        g < 0 ||
        g > 255 ||
        typeof b !== "number" ||
        isNaN(b) ||
        b < 0 ||
        b > 255
    ) {
        return false;
    }
    const rr = r < 16 ? "0" + r.toString(16) : r.toString(16);
    const gg = g < 16 ? "0" + g.toString(16) : g.toString(16);
    const bb = b < 16 ? "0" + b.toString(16) : b.toString(16);
    if (
        typeof a !== "number" ||
        isNaN(a) ||
        a < 0 ||
        a > 100 ||
        Math.abs(a - 100) < Number.EPSILON
    ) {
        return `#${rr}${gg}${bb}`.toUpperCase();
    }
    const alpha = Math.round((a / 100) * 255);
    const aa = alpha < 16 ? "0" + alpha.toString(16) : alpha.toString(16);
    return `#${rr}${gg}${bb}${aa}`.toUpperCase();
}
/**
 * Converts a CSS color (rgb(), rgba(), hexadecimal) to RGBA color components.
 *
 * Note: we don't support using and displaying hexadecimal color with opacity
 * but this method allows to receive one and returns the correct opacity value.
 *
 * @static
 * @param {string} cssColor - hexadecimal code or rgb() or rgba() or color()
 * @returns {Object|false}
 *          - red [0, 255] (integer)
 *          - green [0, 255] (integer)
 *          - blue [0, 255] (integer)
 *          - opacity [0, 100.0] (float)
 */
export function convertCSSColorToRgba(cssColor = "") {
    // Check if cssColor is a rgba() or rgb() color
    const rgba = cssColor.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d*(?:\.\d+)?))?\)$/);
    if (rgba) {
        if (rgba[4] === undefined) {
            rgba[4] = 1;
        }
        return {
            red: parseInt(rgba[1]),
            green: parseInt(rgba[2]),
            blue: parseInt(rgba[3]),
            opacity: Math.round(parseFloat(rgba[4]) * 100),
        };
    }

    // Otherwise, check if cssColor is an hexadecimal code color
    // first check if it's in its compact form (e.g. #FFF)
    if (/^#([0-9a-f]{3})$/i.test(cssColor)) {
        return {
            red: parseInt(cssColor[1] + cssColor[1], 16),
            green: parseInt(cssColor[2] + cssColor[2], 16),
            blue: parseInt(cssColor[3] + cssColor[3], 16),
            opacity: 100,
        };
    }

    if (/^#([0-9A-F]{6}|[0-9A-F]{8})$/i.test(cssColor)) {
        return {
            red: parseInt(cssColor.substr(1, 2), 16),
            green: parseInt(cssColor.substr(3, 2), 16),
            blue: parseInt(cssColor.substr(5, 2), 16),
            opacity: (cssColor.length === 9 ? parseInt(cssColor.substr(7, 2), 16) / 255 : 1) * 100,
        };
    }

    // TODO maybe implement a support for receiving css color like 'red' or
    // 'transparent' (which are now considered non-css color by isCSSColor...)
    // Note: however, if ever implemented be careful of 'white'/'black' which
    // actually are color names for our color system...

    // Check if cssColor is a color() functional notation allowing colorspace
    // with implicit sRGB.
    // "<color()>" allows to define a color specification in a formalized
    // manner. It starts with the "color(" keyword, specifies color space
    // parameters, and optionally includes an alpha value for transparency.
    if (/color\(.+\)/.test(cssColor)) {
        const canvasEl = document.createElement("canvas");
        canvasEl.height = 1;
        canvasEl.width = 1;
        const ctx = canvasEl.getContext("2d");
        ctx.fillStyle = cssColor;
        ctx.fillRect(0, 0, 1, 1);
        const data = ctx.getImageData(0, 0, 1, 1).data;
        return {
            red: data[0],
            green: data[1],
            blue: data[2],
            opacity: data[3] / 2.55, // Convert 0-255 to percentage
        };
    }
    return false;
}
/**
 * Converts a CSS color (rgb(), rgba(), hexadecimal) to a normalized version
 * of the same color (@see convertRgbaToCSSColor).
 *
 * Normalized color can be safely compared using string comparison.
 *
 * @static
 * @param {string} cssColor - hexadecimal code or rgb() or rgba()
 * @returns {string} - the normalized css color or the given css color if it
 *                     failed to be normalized
 */
export function normalizeCSSColor(cssColor) {
    const rgba = convertCSSColorToRgba(cssColor);
    if (!rgba) {
        return cssColor;
    }
    return convertRgbaToCSSColor(rgba.red, rgba.green, rgba.blue, rgba.opacity);
}
/**
 * Checks if a given string is a css color.
 *
 * @static
 * @param {string} cssColor
 * @returns {boolean}
 */
export function isCSSColor(cssColor) {
    return convertCSSColorToRgba(cssColor) !== false;
}
/**
 * Mixes two colors by applying a weighted average of their red, green and blue
 * components.
 *
 * @static
 * @param {string} cssColor1 - hexadecimal code or rgb() or rgba()
 * @param {string} cssColor2 - hexadecimal code or rgb() or rgba()
 * @param {number} weight - a number between 0 and 1
 * @returns {string} - mixed color in hexadecimal format
 */
export function mixCssColors(cssColor1, cssColor2, weight) {
    const rgba1 = convertCSSColorToRgba(cssColor1);
    const rgba2 = convertCSSColorToRgba(cssColor2);
    const rgb1 = [rgba1.red, rgba1.green, rgba1.blue];
    const rgb2 = [rgba2.red, rgba2.green, rgba2.blue];
    const [r, g, b] = rgb1.map((_, idx) =>
        Math.round(rgb2[idx] + (rgb1[idx] - rgb2[idx]) * weight)
    );
    return convertRgbaToCSSColor(r, g, b);
}

/**
 * @param {string} [value]
 * @returns {boolean}
 */
export function isColorGradient(value) {
    return value && value.includes("-gradient(");
}

/**
 * @param {string} gradient
 * @returns {string} standardized gradient
 */
export function standardizeGradient(gradient) {
    if (isColorGradient(gradient)) {
        const el = document.createElement("div");
        el.style.setProperty("background-image", gradient);
        gradient = el.style.getPropertyValue("background-image");
    }
    return gradient;
}

export const RGBA_REGEX = /[\d.]{1,5}/g;

/**
 * Takes a color (rgb, rgba or hex) and returns its hex representation. If the
 * color is given in rgba, the background color of the node whose color we're
 * converting is used in conjunction with the alpha to compute the resulting
 * color (using the formula: `alpha*color + (1 - alpha)*background` for each
 * channel).
 *
 * @param {string} rgb
 * @param {HTMLElement} [node]
 * @returns {string} hexadecimal color (#RRGGBB)
 */
export function rgbToHex(rgb = "", node = null) {
    if (rgb.startsWith("#")) {
        return rgb;
    } else if (rgb.startsWith("rgba")) {
        const values = rgb.match(RGBA_REGEX) || [];
        const alpha = parseFloat(values.pop());
        // Retrieve the background color.
        let bgRgbValues = [];
        if (node) {
            let bgColor = getComputedStyle(node).backgroundColor;
            if (bgColor.startsWith("rgba")) {
                // The background color is itself rgba so we need to compute
                // the resulting color using the background color of its
                // parent.
                bgColor = rgbToHex(bgColor, node.parentElement);
            }
            if (bgColor && bgColor.startsWith("#")) {
                bgRgbValues = (bgColor.match(/[\da-f]{2}/gi) || []).map((val) => parseInt(val, 16));
            } else if (bgColor && bgColor.startsWith("rgb")) {
                bgRgbValues = (bgColor.match(RGBA_REGEX) || []).map((val) => parseInt(val));
            }
        }
        bgRgbValues = bgRgbValues.length ? bgRgbValues : [255, 255, 255]; // Default to white.

        return (
            "#" +
            values
                .map((value, index) => {
                    const converted = Math.floor(
                        alpha * parseInt(value) + (1 - alpha) * bgRgbValues[index]
                    );
                    const hex = parseInt(converted).toString(16);
                    return hex.length === 1 ? "0" + hex : hex;
                })
                .join("")
        );
    } else {
        return (
            "#" +
            (rgb.match(/\d{1,3}/g) || [])
                .map((x) => {
                    x = parseInt(x).toString(16);
                    return x.length === 1 ? "0" + x : x;
                })
                .join("")
        );
    }
}

/**
 * Converts an RGBA or RGB color string to a hexadecimal color string.
 * - If the input color is already in hex format, it returns the hex string directly.
 * - If the input color is in rgba format, it converts it to a hex string, including the alpha value.
 * - If the input color is in rgb format, it converts it to a hex string (with no alpha).
 *
 * @param {string} rgba - The color string to convert (can be in RGBA, RGB, or hex format).
 * @returns {string} - The resulting color in hex format (including alpha if applicable).
 */
export function rgbaToHex(rgba = "") {
    if (rgba.startsWith("#")) {
        return rgba;
    } else if (rgba.startsWith("rgba")) {
        const values = rgba.match(RGBA_REGEX) || [];
        return convertRgbaToCSSColor(
            parseInt(values[0]),
            parseInt(values[1]),
            parseInt(values[2]),
            parseFloat(values[3]) * 100
        );
    } else {
        return rgbToHex(rgba);
    }
}

/**
 * Blends an RGBA color with the background color of a given DOM node.
 * - If the input color is not RGBA, it is converted to hex.
 * - If the node has an RGBA background, the function recursively blends it with its parent's background.
 * - If no valid background is found, it defaults to white (#FFFFFF).
 *
 * @param {string} color - The RGBA color to blend.
 * @param {HTMLElement|null} node - The DOM node to get the background color from.
 * @returns {string} - The resulting blended color as a hex string.
 */
export function blendColors(color, node) {
    if (!color.startsWith("rgba")) {
        return rgbaToHex(color);
    }
    let bgRgbValues = [255, 255, 255];
    if (node) {
        let bgColor = getComputedStyle(node).backgroundColor;

        if (bgColor.startsWith("rgba")) {
            // The background color is itself rgba so we need to compute
            // the resulting color using the background color of its
            // parent.
            bgColor = blendColors(bgColor, node.parentElement);
        }
        if (bgColor.startsWith("#")) {
            bgRgbValues = (bgColor.match(/[\da-f]{2}/gi) || []).map((val) => parseInt(val, 16));
        } else if (bgColor.startsWith("rgb")) {
            bgRgbValues = (bgColor.match(/[\d.]{1,5}/g) || []).map((val) => parseInt(val));
        }
    }

    const values = color.match(/[\d.]{1,5}/g) || [];
    const alpha = values.length === 4 ? parseFloat(values.pop()) : 1;

    return (
        "#" +
        values
            .map((value, index) => {
                const converted = Math.round(
                    alpha * parseInt(value) + (1 - alpha) * bgRgbValues[index]
                );
                const hex = parseInt(converted).toString(16);
                return hex.length === 1 ? "0" + hex : hex;
            })
            .join("")
    );
}
