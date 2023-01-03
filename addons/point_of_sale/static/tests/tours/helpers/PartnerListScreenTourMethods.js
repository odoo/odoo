/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    clickPartner(name) {
        return [
            {
                content: `click partner '${name}' from partner list screen`,
                trigger: `.partnerlist-screen .partner-list-contents .partner-line td:contains("${name}")`,
            },
        ];
    }
}

class Check {
    isShown() {
        return [
            {
                content: "partner list screen is shown",
                trigger: ".pos-content .partnerlist-screen",
                run: () => {},
            },
        ];
    }
}

class Execute {}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("PartnerListScreen", Do, Check, Execute));
