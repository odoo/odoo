/** @odoo-module default=false **/
export const COLORS = [
    "#FFFFFF",
    "#262c34",
    "#f1c40f",
    "#FBB130",
    "#FC787D",
    "#EB5A46",
    "#9b59b6",
    "#0079BF",
    "#1BB6F9",
    "#4dd0e1",
    "#00CEB3",
    "#2ecc71",
];

export const BG_COLORS = [
    "#FFFFFF",
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
];

/**
 * This allows to list Font Awesome icon, independently of the library version
 * Some icons use the same glyph for multiple classes. Those are filtered to only
 * list the icon once
 */
export function getFontAwesomeIcons() {
    const styleSheet = [...document.styleSheets].find(
        (s) => s && s.href && s.href.includes("/web/")
    );
    const fontAwesomeStyles = [...styleSheet.cssRules]
        .filter((e) => /^\.fa-.*:before/.test(e.selectorText))
        .filter((e) => e && e.style && e.style.length === 1 && e.style[0] === "content");
    return fontAwesomeStyles.map((rule) => {
        const classNames = rule.selectorText.split(/:?:before|,/).filter((e) => e.length > 1);
        const searchTerms = classNames.map((selector) =>
            selector.replace(".fa-", "").replace(/-o$/g, " (Outline)").replaceAll("-", " ")
        );
        return {
            className: "fa " + classNames[0].slice(1),
            searchTerms,
            tooltip: searchTerms[0].charAt(0).toUpperCase() + searchTerms[0].slice(1),
        };
    });
}

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
    randomString,
};
