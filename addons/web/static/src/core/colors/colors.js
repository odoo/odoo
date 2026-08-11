import { clamp } from "@web/core/utils/numbers";
/**
 * Lists of colors that contrast well with each other to be used in various
 * visualizations (eg. graphs/charts), both in bright and dark themes.
 */

const COLORS_ENT_BRIGHT = ["#875A7B", "#A5D8D7", "#DCD0D9"];
const COLORS_ENT_DARK = ["#84487D", "#17928D", "#7A4374"];
const COLORS_SM_BRIGHT = [
    "#4EA7F2", // Blue
    "#EA6175", // Red
    "#43C5B1", // Teal
    "#F4A261", // Orange
    "#8481DD", // Purple
    "#FFD86D", // Yellow
];
const COLORS_SM_DARK = [
  "#479FFF", // Blue
  "#E35D71", // Red
  "#02C4A6", // Teal
  "#F08532", // Orange
  "#6760D5", // Purple
  "#F6BB3C"  // Yellow
];
const COLORS_MD_BRIGHT = [
    "#4EA7F2", // Blue #1
    "#3188E6", // Blue #2
    "#43C5B1", // Teal #1
    "#00A78D", // Teal #2
    "#EA6175", // Red #1
    "#CE4257", // Red #2
    "#F4A261", // Orange #1
    "#F48935", // Orange #2
    "#8481DD", // Purple #1
    "#5752D1", // Purple #2
    "#FFD86D", // Yellow #1
    "#FFBC2C", // Yellow #2
];
const COLORS_MD_DARK = [
    "#479FFF", // Blue #1
    "#2F86E5", // Blue #2
    "#02C4A6", // Teal #1
    "#1BA08B", // Teal #2
    "#E35D71", // Red #1
    "#B23D4E", // Red #2
    "#F08532", // Orange #1
    "#CD6613", // Orange #2
    "#6760D5", // Purple #1
    "#4E49A3", // Purple #2
    "#F6BB3C", // Yellow #1
    "#D09518", // Yellow #2
];
const COLORS_LG_BRIGHT = [
    "#4EA7F2", // Blue #1
    "#3188E6", // Blue #2
    "#056BD9", // Blue #3
    "#A76DBC", // Violet #1
    "#7F4295", // Violet #2
    "#6D2387", // Violet #3
    "#EA6175", // Red #1
    "#CE4257", // Red #2
    "#982738", // Red #3
    "#43C5B1", // Teal #1
    "#00A78D", // Teal #2
    "#0E8270", // Teal #3
    "#F4A261", // Orange #1
    "#F48935", // Orange #2
    "#BE5D10", // Orange #3
    "#8481DD", // Purple #1
    "#5752D1", // Purple #2
    "#3A3580", // Purple #3
    "#A4A8B6", // Gray #1
    "#7E8290", // Gray #2
    "#545B70", // Gray #3
    "#FFD86D", // Yellow #1
    "#FFBC2C", // Yellow #2
    "#C08A16", // Yellow #3
];
const COLORS_LG_DARK = [
    "#479FFF", // Blue #1
    "#2F86E5", // Blue #2
    "#2469B5", // Blue #3
    "#8E4FA5", // Violet #1
    "#8631A5", // Violet #2
    "#64287B", // Violet #3
    "#E35D71", // Red #1
    "#B23D4E", // Red #2
    "#8E1F30", // Red #3
    "#02C4A6", // Teal #1
    "#1BA08B", // Teal #2
    "#1B8878", // Teal #3
    "#F08532", // Orange #1
    "#CD6613", // Orange #2
    "#AB4E15", // Orange #3
    "#6760D5", // Purple #1
    "#4E49A3", // Purple #2
    "#333083", // Purple #3
    "#8E94A9", // Gray #1
    "#60677C", // Gray #2
    "#484B5A", // Gray #3
    "#F6BB3C", // Yellow #1
    "#D09518", // Yellow #2
    "#333083", // Yellow #3
];
const COLORS_XL_BRIGHT = [
    "#4EA7F2", // Blue #1
    "#3188E6", // Blue #2
    "#056BD9", // Blue #3
    "#155193", // Blue #4
    "#A76DBC", // Violet #1
    "#7F4295", // Violet #1
    "#6D2387", // Violet #1
    "#4F1565", // Violet #1
    "#EA6175", // Red #1
    "#CE4257", // Red #2
    "#982738", // Red #3
    "#791B29", // Red #4
    "#43C5B1", // Teal #1
    "#00A78D", // Teal #2
    "#0E8270", // Teal #3
    "#105F53", // Teal #4
    "#F4A261", // Orange #1
    "#F48935", // Orange #2
    "#BE5D10", // Orange #3
    "#7D380D", // Orange #4
    "#8481DD", // Purple #1
    "#5752D1", // Purple #2
    "#3A3580", // Purple #3
    "#26235F", // Purple #4
    "#A4A8B6", // Grey #1
    "#7E8290", // Grey #2
    "#545B70", // Grey #3
    "#3F4250", // Grey #4
    "#FFD86D", // Yellow #1
    "#FFBC2C", // Yellow #2
    "#C08A16", // Yellow #3
    "#936A12", // Yellow #4
];
const COLORS_XL_DARK = [
    "#72BEFF", // Blue #1
    "#479FFF", // Blue #2
    "#2F86E5", // Blue #3
    "#2469B5", // Blue #4
    "#B47CC9", // Violet #1
    "#8E4FA5", // Violet #2
    "#8631A5", // Violet #3
    "#64287B", // Violet #4
    "#FC8596", // Red #1
    "#E35D71", // Red #2
    "#B23D4E", // Red #3
    "#8E1F30", // Red #4
    "#4BE3CB", // Teal #1
    "#02C4A6", // Teal #2
    "#1BA08B", // Teal #3
    "#1B8878", // Teal #4
    "#FCA865", // Orange #1
    "#F08532", // Orange #2
    "#CD6613", // Orange #3
    "#AB4E15", // Orange #4
    "#837BFF", // Purple #1
    "#6760D5", // Purple #2
    "#4E49A3", // Purple #3
    "#333083", // Purple #4
    "#BFC2CE", // Grey #1
    "#8E94A9", // Grey #2
    "#60677C", // Grey #3
    "#484B5A", // Grey #4
    "#F7D67C", // Yellow #1
    "#F6BB3C", // Yellow #2
    "#D09518", // Yellow #3
    "#A6740A", // Yellow #4
];

/**
 * @param {string} colorScheme
 * @param {string} paletteName
 * @returns {array}
 */
export function getColors(colorScheme, paletteName) {
    switch (paletteName) {
        case "odoo":
            return colorScheme === "dark" ? COLORS_ENT_DARK : COLORS_ENT_BRIGHT;
        case "sm":
            return colorScheme === "dark" ? COLORS_SM_DARK : COLORS_SM_BRIGHT;
        case "md":
            return colorScheme === "dark" ? COLORS_MD_DARK : COLORS_MD_BRIGHT;
        case "lg":
            return colorScheme === "dark" ? COLORS_LG_DARK : COLORS_LG_BRIGHT;
        default:
            return colorScheme === "dark" ? COLORS_XL_DARK : COLORS_XL_BRIGHT;
    }
}

/**
 * @param {number} index
 * @param {string} colorScheme
 * @returns {string}
 */
export function getColor(index, colorScheme, paletteSizeOrName) {
    let paletteName;
    if (paletteSizeOrName === "odoo") {
        paletteName = "odoo";
    } else if (paletteSizeOrName <= 6 || paletteSizeOrName === "sm") {
        paletteName = "sm";
    } else if (paletteSizeOrName <= 12 || paletteSizeOrName === "md") {
        paletteName = "md";
    } else if (paletteSizeOrName <= 24 || paletteSizeOrName === "lg") {
        paletteName = "lg";
    } else {
        paletteName = "xl";
    }
    const colors = getColors(colorScheme, paletteName);
    return colors[index % colors.length];
}

export const DEFAULT_BG = "#d3d3d3";

export function getBorderWhite(colorScheme) {
    return colorScheme === "dark" ? "rgba(38, 42, 54, .2)" : "rgba(249,250,251, .2)";
}

const RGB_REGEX = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i;

/**
 * @param {string} hex
 * @param {number} opacity
 * @returns {string}
 */
export function hexToRGBA(hex, opacity) {
    const rgb = RGB_REGEX.exec(hex)
        .slice(1, 4)
        .map((n) => parseInt(n, 16))
        .join(",");
    return `rgba(${rgb},${opacity})`;
}

/**
 * Used to return custom colors depending on the color scheme
 * @param {string} colorScheme
 * @param {string} brightModeColor
 * @param {string} darkModeColor
 * @returns {string|Number|Boolean}
 */

export function getCustomColor(colorScheme, brightModeColor, darkModeColor) {
    if (darkModeColor === undefined) {
        return brightModeColor;
    } else {
        return colorScheme === "dark" ? darkModeColor : brightModeColor;
    }
}

/**
 * Used to lighten a color
 * @param {string} color
 * @param {number} factor
 * @returns {string}
 */
export function lightenColor(color, factor) {
    factor = clamp(factor, 0, 1);

    let r = parseInt(color.substring(1, 3), 16);
    let g = parseInt(color.substring(3, 5), 16);
    let b = parseInt(color.substring(5, 7), 16);

    r = Math.round(r + (255 - r) * factor);
    g = Math.round(g + (255 - g) * factor);
    b = Math.round(b + (255 - b) * factor);

    r = r.toString(16).padStart(2, "0");
    g = g.toString(16).padStart(2, "0");
    b = b.toString(16).padStart(2, "0");

    return `#${r}${g}${b}`;
}

/**
 * Used to darken a color
 * @param {string} color
 * @param {number} factor
 * @returns {string}
 */
export function darkenColor(color, factor) {
    factor = clamp(factor, 0, 1);

    let r = parseInt(color.substring(1, 3), 16);
    let g = parseInt(color.substring(3, 5), 16);
    let b = parseInt(color.substring(5, 7), 16);

    r = Math.round(r * (1 - factor));
    g = Math.round(g * (1 - factor));
    b = Math.round(b * (1 - factor));

    r = r.toString(16).padStart(2, "0");
    g = g.toString(16).padStart(2, "0");
    b = b.toString(16).padStart(2, "0");

    return `#${r}${g}${b}`;
}
