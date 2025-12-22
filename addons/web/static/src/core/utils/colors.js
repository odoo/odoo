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
    if (typeof (r) !== 'number' || isNaN(r) || r < 0 || r > 255
            || typeof (g) !== 'number' || isNaN(g) || g < 0 || g > 255
            || typeof (b) !== 'number' || isNaN(b) || b < 0 || b > 255) {
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
};
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
    if (typeof (h) !== 'number' || isNaN(h) || h < 0 || h > 360
            || typeof (s) !== 'number' || isNaN(s) || s < 0 || s > 100
            || typeof (l) !== 'number' || isNaN(l) || l < 0 || l > 100) {
        return false;
    }

    var huePrime = h / 60;
    var saturation = s / 100;
    var lightness = l / 100;
    var chroma = saturation * (1 - Math.abs(2 * lightness - 1));
    var secondComponent = chroma * (1 - Math.abs(huePrime % 2 - 1));
    var lightnessAdjustment = lightness - chroma / 2;
    var precision = 255;
    chroma = Math.round((chroma + lightnessAdjustment) * precision);
    secondComponent = Math.round((secondComponent + lightnessAdjustment) * precision);
    lightnessAdjustment = Math.round((lightnessAdjustment) * precision);
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
};
/**
 * Converts RGBA color components to a normalized CSS color: if the opacity
 * is invalid or equal to 100, a hex is returned; otherwise a rgba() css color
 * is returned.
 *
 * Those choice have multiple reason:
 * - A hex color is more common to c/c from other utilities on the web and is
 *   also shorter than rgb() css colors
 * - Opacity in hexadecimal notations is not supported on all browsers and is
 *   also less common to use.
 *
 * @static
 * @param {integer} r - [0, 255]
 * @param {integer} g - [0, 255]
 * @param {integer} b - [0, 255]
 * @param {float} a - [0, 100]
 * @returns {string}
 */
export function convertRgbaToCSSColor(r, g, b, a) {
    if (typeof (r) !== 'number' || isNaN(r) || r < 0 || r > 255
            || typeof (g) !== 'number' || isNaN(g) || g < 0 || g > 255
            || typeof (b) !== 'number' || isNaN(b) || b < 0 || b > 255) {
        return false;
    }
    if (typeof (a) !== 'number' || isNaN(a) || a < 0 || Math.abs(a - 100) < Number.EPSILON) {
        const rr = r < 16 ? '0' + r.toString(16) : r.toString(16);
        const gg = g < 16 ? '0' + g.toString(16) : g.toString(16);
        const bb = b < 16 ? '0' + b.toString(16) : b.toString(16);
        return (`#${rr}${gg}${bb}`).toUpperCase();
    }
    return `rgba(${r}, ${g}, ${b}, ${parseFloat((a / 100.0).toFixed(3))})`;
};
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
export function convertCSSColorToRgba(cssColor) {
    // Check if cssColor is a rgba() or rgb() color
    const rgba = cssColor.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+(?:\.\d+)?))?\)$/);
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
    if (/^#([0-9A-F]{6}|[0-9A-F]{8})$/i.test(cssColor)) {
        return {
            red: parseInt(cssColor.substr(1, 2), 16),
            green: parseInt(cssColor.substr(3, 2), 16),
            blue: parseInt(cssColor.substr(5, 2), 16),
            opacity: (cssColor.length === 9 ? (parseInt(cssColor.substr(7, 2), 16) / 255) : 1) * 100,
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
};
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
};
/**
 * Checks if a given string is a css color.
 *
 * @static
 * @param {string} cssColor
 * @returns {boolean}
 */
export function isCSSColor(cssColor) {
    return convertCSSColorToRgba(cssColor) !== false;
};
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
    const [r, g, b] = rgb1.map((_, idx) => Math.round(rgb2[idx] + (rgb1[idx] - rgb2[idx]) * weight));
    return convertRgbaToCSSColor(r, g, b);
};
