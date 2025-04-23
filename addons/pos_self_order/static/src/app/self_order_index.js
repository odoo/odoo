import { Component, whenReady } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { Router } from "@pos_self_order/app/router";
import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { ComboPage } from "@pos_self_order/app/pages/combo_page/combo_page";
import { ProductPage } from "@pos_self_order/app/pages/product_page/product_page";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";
import { EatingLocationPage } from "@pos_self_order/app/pages/eating_location_page/eating_location_page";
import { KioskCategoryListPage } from "@pos_self_order/app/pages/kiosk_category_list_page/kiosk_category_list_page";
import { KioskProductListPage } from "@pos_self_order/app/pages/kiosk_product_list_page/kiosk_product_list_page";
import { KioskComboPage } from "@pos_self_order/app/pages/kiosk_combo_page/kiosk_combo_page";
import { KioskProductPage } from "@pos_self_order/app/pages/kiosk_product_page/kiosk_product_page";
import { KioskCartPage } from "@pos_self_order/app/pages/kiosk_card_page/kiosk_cart_page";

import { StandNumberPage } from "@pos_self_order/app/pages/stand_number_page/stand_number_page";
import { OrdersHistoryPage } from "@pos_self_order/app/pages/order_history_page/order_history_page";
import { LoadingOverlay } from "@pos_self_order/app/components/loading_overlay/loading_overlay";
import { mountComponent } from "@web/env";
import { hasTouch } from "@web/core/browser/feature_detection";
import { init as initDebugFormatters } from "@point_of_sale/app/utils/debug-formatter";
import { insertKioskStyle } from "./kiosk_style";

export class selfOrderIndex extends Component {
    static template = "pos_self_order.selfOrderIndex";
    static props = [];
    static components = {
        Router,
        CartPage,
        ProductPage,
        OrdersHistoryPage,
        ComboPage,
        PaymentPage,
        ConfirmationPage,
        ProductListPage,
        KioskProductListPage,
        KioskComboPage,
        KioskCategoryListPage,
        KioskCartPage,
        EatingLocationPage,
        KioskProductPage,
        StandNumberPage,
        LandingPage,
        LoadingOverlay,
        MainComponentsContainer,
    };

    setup() {
        this.selfOrder = useSelfOrder();
        window.posmodel = this.selfOrder;

        // Disable cursor on touch devices (required on IoT Box Kiosk)
        if (hasTouch()) {
            document.body.classList.add("touch-device");
        }

        if (this.selfOrder.kioskMode) {
            const styleConfig = this.selfOrder.config._self_ordering_style;
            if (styleConfig) {
                const { primaryBgColor, primaryTextColor } = styleConfig;
                insertKioskStyle(primaryBgColor, primaryTextColor);
            }
            document.body.classList.add("kiosk");
        }

        if (this.env.debug) {
            initDebugFormatters();
        }
    }
    get selfIsReady() {
        return this.selfOrder.models["product.product"].length > 0;
    }
}
whenReady(() => mountComponent(selfOrderIndex, document.body));
