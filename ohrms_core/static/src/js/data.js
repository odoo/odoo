/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

function oHrmsAccountItem(env) {
    const url = "https://www.openhrms.com/";
    return {
        type: "item",
        id: "ohrms_account",
        description: env._t("Open HRMS"),
        href: url,
        callback: () => {
            browser.open(url, "_blank");
        },
        sequence: 20,
    };
}

registry.category("user_menuitems")
registry.add("oHrmsAccountItem",oHrmsAccountItem)
