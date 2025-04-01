import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { LanguagePopup } from "@pos_self_order/app/components/language_popup/language_popup";

export class EatingLocationPage extends Component {
    static template = "pos_self_order.EatingLocationPage";
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
    }

    back() {
        this.router.navigate("default");
    }

    selectPreset(preset) {
        this.selfOrder.currentOrder.setPreset(preset);
        this.selfOrder.currentTable = null;

        if (this.selfOrder.kioskMode) {
            this.router.navigate("category_list");
            return;
        }

        this.router.navigate("product_list");
    }

    get presets() {
        return this.selfOrder.models["pos.preset"].getAll();
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

    get backgroundImage() {
        const bgImage = this.selfOrder.config._self_ordering_image_background_ids[0];
        if (bgImage) {
            return `url(data:image/png;base64,${bgImage.data})`;
        }
        return "none";
    }
}
