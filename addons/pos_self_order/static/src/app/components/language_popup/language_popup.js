import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
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
        if (language === this.currentLanguage) {
            this.props.close();
            return;
        }

        cookie.set("frontend_lang", language.code);

        const currentUrl = new URL(window.location.href);
        const fullLangCode = this.currentLanguage.code.toLowerCase();
        const baseLangCode = fullLangCode.split("_")[0];
        const langPrefixPattern = new RegExp(`^/(?:${fullLangCode}|${baseLangCode})(/|$)`, "i");
        if (langPrefixPattern.test(currentUrl.pathname)) {
            currentUrl.pathname = currentUrl.pathname.replace(langPrefixPattern, "/");
            window.location.href = currentUrl.href;
        } else {
            window.location.reload();
        }
    }
}
