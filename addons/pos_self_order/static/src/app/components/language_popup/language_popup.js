/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";

export class LanguagePopup extends Component {
    static template = "pos_self_order.LanguagePopup";

    setup() {
        this.selfOrder = useSelfOrder();
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
