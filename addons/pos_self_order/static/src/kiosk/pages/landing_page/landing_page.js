/** @odoo-module */

import { Component, onWillStart } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";
import { LanguagePopup } from "@pos_self_order/kiosk/components/language_popup/language_popup";
import { Order } from "@pos_self_order/common/models/order";

export class LandingPage extends Component {
    static template = "pos_self_order.LandingPage";
    static components = { KioskTemplate };

    setup() {
        this.selfOrder = useselfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");

        onWillStart(() => {
            this.selfOrder.currentOrder = new Order({});
            this.tablePadNumber = null;
        });
    }

    start() {
        if (this.selfOrder.kiosk_takeaway) {
            this.router.navigate("location");
        } else {
            this.router.navigate("product_list");
        }
    }

    openLanguages() {
        this.dialog.add(LanguagePopup);
    }

    get currentLanguage() {
        return this.selfOrder.currentLanguage;
    }

    get languages() {
        return this.selfOrder.kiosk_available_languages;
    }
}
