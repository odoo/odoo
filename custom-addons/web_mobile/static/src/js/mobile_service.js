/** @odoo-module **/

import { registry } from "@web/core/registry";

import mobile from "@web_mobile/js/services/core";
import { shortcutItem, switchAccountItem } from "./user_menu_items";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");

const mobileService = {
    start() {
        if (mobile.methods.addHomeShortcut) {
            userMenuRegistry.add("web_mobile.shortcut", shortcutItem);
        }

        if (mobile.methods.switchAccount) {
            // remove "Log Out" and "My Odoo.com Account"
            userMenuRegistry.remove('log_out');
            userMenuRegistry.remove('odoo_account');

            userMenuRegistry.add("web_mobile.switch", switchAccountItem);
        }
    },
};
serviceRegistry.add("mobile", mobileService);
