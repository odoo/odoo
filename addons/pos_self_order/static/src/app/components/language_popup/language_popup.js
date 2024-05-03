import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { cookie } from "@web/core/browser/cookie";

export class LanguagePopup extends Component {
    static template = "pos_self_order.LanguagePopup";
    static props = {
        close: Function,
    };

    setup() {
        this.selfOrder = useSelfOrder();
    }

    get languages() {
        return this.selfOrder.config.self_ordering_available_language_ids;
    }

    get currentLanguage() {
        return this.selfOrder.currentLanguage;
    }

    onClickLanguage(language) {
        cookie.set("frontend_lang", language.code);
        window.location.reload();
    }
}
