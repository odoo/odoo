/** @odoo-module */

const VIEW_PREFIX = "odoo://view/";
const IR_MENU_ID_PREFIX = "odoo://ir_menu_id/";
const IR_MENU_XML_ID_PREFIX = "odoo://ir_menu_xml_id/";

/**
 * @typedef Action
 * @property {Array} domain
 * @property {Object} context
 * @property {string} modelName
 * @property {string} orderBy
 * @property {Array<[boolean, string]>} views
 *
 * @typedef ViewLinkDescription
 * @property {string} name Action name
 * @property {Action} action
 * @property {string} viewType Type of view (list, pivot, ...)
 */

/**
 *
 * @param {string} url
 * @returns {boolean}
 */
export function isMarkdownViewUrl(url) {
    return url.startsWith(VIEW_PREFIX);
}

/**
 *
 * @param {string} viewLink
 * @returns {ViewLinkDescription}
 */
export function parseViewLink(viewLink) {
    if (viewLink.startsWith(VIEW_PREFIX)) {
        return JSON.parse(viewLink.substring(VIEW_PREFIX.length));
    }
    throw new Error(`${viewLink} is not a valid view link`);
}

/**
 * @param {ViewLinkDescription} viewDescription Id of the ir.filter
 * @returns {string}
 */
export function buildViewLink(viewDescription) {
    return `${VIEW_PREFIX}${JSON.stringify(viewDescription)}`;
}

/**
 *
 * @param {string} url
 * @returns {boolean}
 */
export function isMarkdownIrMenuIdUrl(url) {
    return url.startsWith(IR_MENU_ID_PREFIX);
}

/**
 *
 * @param {string} irMenuLink
 * @returns ir.ui.menu record id
 */
export function parseIrMenuIdLink(irMenuLink) {
    if (irMenuLink.startsWith(IR_MENU_ID_PREFIX)) {
        return parseInt(irMenuLink.substring(IR_MENU_ID_PREFIX.length), 10);
    }
    throw new Error(`${irMenuLink} is not a valid menu id link`);
}

/**
 * @param {number} menuId
 * @returns
 */
export function buildIrMenuIdLink(menuId) {
    return `${IR_MENU_ID_PREFIX}${menuId}`;
}

/**
 *
 * @param {string} url
 * @returns {boolean}
 */
export function isIrMenuXmlUrl(url) {
    return url.startsWith(IR_MENU_XML_ID_PREFIX);
}

/**
 *
 * @param {string} irMenuUrl
 * @returns {string} ir.ui.menu record id
 */
export function parseIrMenuXmlUrl(irMenuUrl) {
    if (irMenuUrl.startsWith(IR_MENU_XML_ID_PREFIX)) {
        return irMenuUrl.substring(IR_MENU_XML_ID_PREFIX.length);
    }
    throw new Error(`${irMenuUrl} is not a valid menu xml link`);
}
/**
 * @param {number} menuXmlId
 * @returns
 */
export function buildIrMenuXmlLink(menuXmlId) {
    return `${IR_MENU_XML_ID_PREFIX}${menuXmlId}`;
}
