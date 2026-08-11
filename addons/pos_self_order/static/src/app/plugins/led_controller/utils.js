export const SUCCESS_COLOR = "0,255,0";
export const ERROR_COLOR = "255,0,0";
export const ODOO_COLOR = "113,75,103";
export const ANIMATION_DURATION_MS = 1500;
export const TIMEOUT_MS = 1000;

const IS_HEX_REGEX = /^#?([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
const VERSION_REGEX = /^\d+(\.\d+)*$/;

/**
 * Applies gamma correction (2.2) to a color channel.
 *
 * @param {number} color - Original color value (0-255).
 * @returns {number} Gamma-corrected value.
 */
export function applyGamma(color) {
    return 255 * Math.pow(color / 255, 2.2);
}

/**
 * Calibrates a web RGB color for LEDs by applying gamma correction
 * and adjusting the white balance (dimming green and blue).
 *
 * @param {string} color - The RGB color string (e.g., "113,75,103").
 * @returns {string} Calibrated RGB string (e.g., "43,12,33").
 */
export function getCalibratedLedColor(color) {
    const [r, g, b] = color.split(",").map(Number);

    const gammaR = applyGamma(r);
    const gammaG = applyGamma(g);
    const gammaB = applyGamma(b);

    const finalR = gammaR * 1.0;
    const finalG = gammaG * 0.68;
    const finalB = gammaB * 0.94;
    return `${Math.round(finalR)},${Math.round(finalG)},${Math.round(finalB)}`;
}

/**
 * Converts a hexadecimal color string to an RGB string format.
 *
 * @param {string} hex - The hexadecimal color string (e.g., "#FFF" or "FFFFFF").
 * @returns {string} RGB string (e.g., "43,12,33").
 */
export function hexToRgb(hex) {
    if (!hex || typeof hex !== "string" || !IS_HEX_REGEX.test(hex)) {
        return false;
    }

    hex = hex.replace(/^#/, "");

    if (hex.length === 3) {
        hex = hex
            .split("")
            .map((char) => char + char)
            .join("");
    }

    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);

    return `${r},${g},${b}`;
}

/**
 * Compares an actual version string with a required version string.
 *
 * @param {string} requiredVersion - The minimum version required.
 * @param {string} actualVersion - The version currently installed/running.
 * @returns {number|boolean} Returns 1, 0, or -1 based on the comparison, or false if invalid.
 */
export function compareVersion(requiredVersion, actualVersion) {
    if (!actualVersion || typeof actualVersion !== "string" || !VERSION_REGEX.test(actualVersion)) {
        return false;
    }
    if (
        !requiredVersion ||
        typeof requiredVersion !== "string" ||
        !VERSION_REGEX.test(requiredVersion)
    ) {
        return false;
    }
    return actualVersion.localeCompare(requiredVersion, undefined, {
        numeric: true,
        sensitivity: "base",
    });
}
