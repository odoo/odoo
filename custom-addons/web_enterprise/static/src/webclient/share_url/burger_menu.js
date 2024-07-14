/** @odoo-module **/

import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { patch } from "@web/core/utils/patch";
import { BurgerMenu } from "@web/webclient/burger_menu/burger_menu";
import { shareUrl } from "./share_url";

if (navigator.share && isDisplayStandalone()) {
    patch(BurgerMenu.prototype, {
        shareUrl,
    });

    patch(BurgerMenu, {
        template: "web_enterprise.BurgerMenu",
    });
}
