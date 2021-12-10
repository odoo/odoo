/** @odoo-module */

const broadlyFalsyLowerCaseStrings = ["false", "", "undefined", "none", "0"];

export function isBroadlyFalsy(value) {
    if (!value) {
        return true;
    }
    if (typeof value === "string") {
        if (broadlyFalsyLowerCaseStrings.includes(value.toLowerCase())) {
            return true;
        }
    }
    return false;
}
