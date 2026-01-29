/** @odoo-module */

export function getFirstElementForXpath(target, xpath) {
    const xPathResult = document.evaluate(xpath, target, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
    return xPathResult.singleNodeValue;
}
