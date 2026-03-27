/** @odoo-module */

import { registries } from "@odoo/o-spreadsheet";

const { urlRegistry } = registries;
const NEUTRALIZED_LINK = "neutralized:link";

export function getNeutralizedLink() {
    return NEUTRALIZED_LINK;
}

export function isNeutralizedLink(url) {
    return url === NEUTRALIZED_LINK;
}

urlRegistry.add("neutralizedLink", {
    sequence: 80,
    match: isNeutralizedLink,
    createLink(url, label) {
        return {
            url,
            label: label,
            isExternal: false,
            isUrlEditable: false,
        };
    },
    urlRepresentation(url) {
        return "";
    },
    open(url) {
        return;
    },
});
