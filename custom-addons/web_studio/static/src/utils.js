/** @odoo-module default=false **/
export const COLORS = [
    "#FFFFFF",
    "#262c34",
    "#00dec9",
    "#2ecc71",
    "#f1c40f",
    "#FFAB4A",
    "#EB5A46",
    "#9b59b6",
    "#0079BF",
    "#4dd0e1",
];

export const BG_COLORS = [
    "#1abc9c",
    "#58a177",
    "#B4C259",
    "#56829f",
    "#636DA9",
    "#34495e",
    "#BC4242",
    "#C6572A",
    "#d49054",
    "#D89F45",
    "#DAB852",
    "#606060",
    "#6B6C70",
    "#838383",
    "#FFFFFF",
];

export const ICONS = [
    "fa fa-diamond",
    "fa fa-bell",
    "fa fa-calendar",
    "fa fa-circle",
    "fa fa-cube",
    "fa fa-cubes",
    "fa fa-flag",
    "fa fa-folder-open",
    "fa fa-home",
    "fa fa-rocket",
    "fa fa-sitemap",
    "fa fa-area-chart",
    "fa fa-balance-scale",
    "fa fa-database",
    "fa fa-globe",
    "fa fa-institution",
    "fa fa-random",
    "fa fa-umbrella",
    "fa fa-bed",
    "fa fa-bolt",
    "fa fa-commenting",
    "fa fa-envelope",
    "fa fa-flask",
    "fa fa-magic",
    "fa fa-pie-chart",
    "fa fa-retweet",
    "fa fa-shopping-basket",
    "fa fa-star",
    "fa fa-television",
    "fa fa-tree",
    "fa fa-thumbs-o-up",
    "fa fa-file-o",
    "fa fa-wheelchair",
    "fa fa-code",
    "fa fa-spinner",
    "fa fa-ticket",
    "fa fa-shield",
    "fa fa-recycle",
    "fa fa-phone",
    "fa fa-microphone",
    "fa fa-magnet",
    "fa fa-info",
    "fa fa-inbox",
    "fa fa-heart",
    "fa fa-bullseye",
    "fa fa-cutlery",
    "fa fa-credit-card",
    "fa fa-briefcase",
];

/**
 * @param {Integer} string_length
 * @returns {String} A random string with numbers and lower/upper case chars
 */
export function randomString(string_length) {
    var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    var randomstring = "";
    for (var i = 0; i < string_length; i++) {
        var rnum = Math.floor(Math.random() * chars.length);
        randomstring += chars.substring(rnum, rnum + 1);
    }
    return randomstring;
}

export default {
    BG_COLORS,
    COLORS,
    ICONS,
    randomString,
};
