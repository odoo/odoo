import { Component, onWillStart } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { LanguagePopup } from "@pos_self_order/app/components/language_popup/language_popup";
export class KioskCategoryListPage extends Component {
    static template = "pos_self_order.KioskCategoryListPage";
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");

        onWillStart(() => {
            this.selfOrder.computeAvailableCategories();
        });
    }

    back() {
        if (this.selfOrder.hasPresets()) {
            this.router.navigate("location");
        } else {
            this.router.navigate("default");
        }
    }

    selectCategory(category) {
        this.selfOrder.currentCategory = category;
        this.router.navigate("product_list");
    }

    get categories() {
        return this.selfOrder.availableCategories;
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
