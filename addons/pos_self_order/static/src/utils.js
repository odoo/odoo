/** @odoo-module */

export const extractProductNameAndAttributes = (str) => {
    const regex = /\(([^()]+)\)[^(]*$/;
    const matches = str.match(regex);

    if (matches && matches.length > 1) {
        const attributes = matches[matches.length - 1].trim();
        const productName = str.replace(matches[0], "").trim();
        return { productName, attributes };
    }

    return { productName: str, attributes: "" };
};
