/** @odoo-module */

import { Component, onMounted, useState } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";

export class PaymentSuccess extends Component {
    static template = "pos_self_order.PaymentSuccess";
    static components = { KioskTemplate };

    setup() {
        this.selfOrder = useselfOrder();
        this.selfOrder.isOrder();
        this.router = useService("router");
        this.cookie = useService("cookie");
        this.state = useState({
            onReload: false,
        });

        onMounted(() => {
            setTimeout(() => {
                this.setDefautLanguage();
            }, 5000);
        });
    }

    backToHome() {
        if (!this.setDefautLanguage()) {
            this.router.navigate("default");
        }
    }

    setDefautLanguage() {
        if (
            this.selfOrder.currentLanguage.code !== this.selfOrder.kiosk_default_language.code &&
            !this.state.onReload
        ) {
            this.cookie.setCookie("frontend_lang", this.selfOrder.kiosk_default_language.code);
            window.location.reload();
            this.state.onReload = true;
            return true;
        }

        return this.state.onReload;
    }
}
