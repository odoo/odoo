odoo.define('web/static/src/js/views/graph/graph_utils', function (require) {
"use strict";

const { device } = require("web.config");

const COLORS = [
    "#1f77b4", "#ff7f0e", "#aec7e8", "#ffbb78", "#2ca02c", "#98df8a", "#d62728",
    "#ff9896", "#9467bd", "#c5b0d5", "#8c564b", "#c49c94", "#e377c2", "#f7b6d2",
    "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5",
];
const DEFAULT_BG = "#d3d3d3";
// used to format values in tooltips and yAxes.
const FORMAT_OPTIONS = {
    // allow to decide if utils.human_number should be used
    humanReadable: value => Math.abs(value) >= 1000,
    // with the choices below, 1236 is represented by 1.24k
    minDigits: 1,
    decimals: 2,
    // avoid comma separators for thousands in numbers when human_number is used
    formatterCallback: str => str,
};
// hide top legend when too many items for device size
const MAX_LEGEND_LENGTH = 4 * Math.max(1, device.size_class);
const RGB_REGEX = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i;

/**
 * @param {number} index
 * @returns {string}
 */
function getColor(index) {
    return COLORS[index % COLORS.length];
}

/**
 * @param {Object} chartArea
 * @returns {string}
 */
function getMaxWidth({ left, right }) {
    return Math.floor((right - left) / 1.618) + "px";
}

/**
 * @param {string} hex
 * @param {number} opacity
 * @returns {string}
 */
function hexToRGBA(hex, opacity) {
    const rgb = RGB_REGEX
        .exec(hex)
        .slice(1, 4)
        .map(n => parseInt(n, 16))
        .join(",");
    return `rgba(${rgb},${opacity})`;
}

/**
 * Used to avoid too long legend items.
 * @param {string} label
 * @returns {string} shortened version of the input label
 */
function shortenLabel(label) {
    // string returned could be wrong if a groupby value contain a "/"!
    const groups = label.split("/");
    let shortLabel = groups.slice(0, 3).join("/");
    if (shortLabel.length > 30) {
        shortLabel = `${shortLabel.slice(0, 30)}...`;
    } else if (groups.length > 3) {
        shortLabel = `${shortLabel}/...`;
    }
    return shortLabel;
}

return {
    COLORS,
    DEFAULT_BG,
    FORMAT_OPTIONS,
    MAX_LEGEND_LENGTH,
    RGB_REGEX,
    getColor,
    getMaxWidth,
    hexToRGBA,
    shortenLabel,
};

});

