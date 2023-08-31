/** @odoo-module */

import { Component } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";

export class LanguagePopup extends Component {
    static template = "pos_self_order.LanguagePopup";

    setup() {
        this.selfOrder = useselfOrder();
        this.cookie = useService("cookie");
    }

    get languages() {
        return this.selfOrder.kiosk_available_languages;
    }

    get currentLanguage() {
        return this.selfOrder.currentLanguage;
    }

    onClickLanguage(language) {
        this.cookie.setCookie("frontend_lang", language.code);
        window.location.reload();
    }
}
