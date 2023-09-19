/** @odoo-module */

import { Component, onMounted, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";

// This component is only use in Kiosk mode
export class PaymentSuccessPage extends Component {
    static template = "pos_self_order.PaymentSuccessPage";

    setup() {
        this.selfOrder = useSelfOrder();
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
        const defaultLanguage = this.selfOrder.config.self_ordering_default_language_id;
        if (this.selfOrder.currentLanguage.code !== defaultLanguage.code && !this.state.onReload) {
            this.cookie.setCookie("frontend_lang", defaultLanguage.code);
            window.location.reload();
            this.state.onReload = true;
            return true;
        }

        return this.state.onReload;
    }
}
