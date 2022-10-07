/** @odoo-module **/

import { getCookie } from "web.utils.cookies";

const COLORS_BRIGHT = [
    "#1f77b4",
    "#ff7f0e",
    "#aec7e8",
    "#ffbb78",
    "#2ca02c",
    "#98df8a",
    "#d62728",
    "#ff9896",
    "#9467bd",
    "#c5b0d5",
    "#875a7b", // ~ Enterprise
    "#c49c94",
    "#e377c2",
    "#dcd0d9", // Dashboards Primary
    "#7f7f7f",
    "#c7c7c7",
    "#bcbd22",
    "#dbdb8d",
    "#17becf",
    "#a5d8d7", // Dashboards Secondary
];

const COLORS_DARK = [
    "#00ffff",
    "#ff6347",
    "#00ced1",
    "#ffd700",
    "#29ef29",
    "#c5fabb",
    "#fe4b4c",
    "#ffb6c1",
    "#ba87e9",
    "#eadbf6",
    "#c568af", // ~ Enterprise
    "#ecc1b8",
    "#fda9e3",
    "#BB86FC", // Dashboards Primary
    "#808080",
    "#f2e8e8",
    "#fcfe2d",
    "#f8f8bc",
    "#17becf",
    "#10efed", // Dashboards Secondary
];

export const COLORS = getCookie("color_scheme") === "dark" ? COLORS_DARK : COLORS_BRIGHT;

/**
 * @param {number} index
 * @returns {string}
 */
export function getColor(index) {
    return COLORS[index % COLORS.length];
}

export const DEFAULT_BG = "#d3d3d3";

export const BORDER_WHITE =
    getCookie("color_scheme") === "dark" ? "rgba(0, 0, 0, 0.6)" : "rgba(255,255,255,0.6)";

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
