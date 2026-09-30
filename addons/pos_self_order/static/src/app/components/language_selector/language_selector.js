import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { LanguagePopup } from "@pos_self_order/app/components/language_popup/language_popup";
import { useService } from "@web/core/utils/hooks";

export class LanguageSelector extends Component {
    static template = "pos_self_order.LanguageSelector";
    static props = { extraClass: { type: String, optional: true } };
    static defaultProps = { extraClass: "" };

    setup() {
        this.selfOrder = useSelfOrder();
        this.dialog = useService("dialog");
    }

    get currentLanguage() {
        return this.selfOrder.currentLanguage;
    }

    get languages() {
        return this.selfOrder.config.self_ordering_available_language_ids;
    }

    openLanguages() {
        this.dialog.add(LanguagePopup);
    }
}
