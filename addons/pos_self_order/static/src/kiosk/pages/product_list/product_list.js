/** @odoo-module */

import { Component, onMounted, useRef } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { ProductCard } from "@pos_self_order/kiosk/components/product_card/product_card";
import { CancelPopup } from "@pos_self_order/kiosk/components/cancel_popup/cancel_popup";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";
import { useService, useChildRef } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class ProductList extends Component {
    static template = "pos_self_order.ProductList";
    static components = { ProductCard, KioskTemplate };

    setup() {
        this.selfOrder = useselfOrder();
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.productsList = useRef("productsList");
        this.currentProductCard = useChildRef();

        onMounted(() => {
            if (this.selfOrder.lastEditedProductId) {
                this.scrollTo(this.currentProductCard, { behavior: "instant" });
            }
        });
    }

    categoryClicked(categoryName) {
        this.selfOrder.currentCategory = categoryName;
    }

    get productCategory() {
        const productByCat = this.selfOrder.productsGroupedByCategory;
        const currentCategory = this.selfOrder.currentCategory;
        return productByCat[currentCategory] ? productByCat[currentCategory] : [];
    }

    scrollTo(ref = null, { behavior = "smooth" } = {}) {
        this.productsList.el.scroll({
            top: ref?.el ? ref.el.offsetTop - this.productsList.el.offsetTop : 0,
            behavior,
        });
    }

    review() {
        this.router.navigate("cart");
    }

    cancelOrder() {
        this.dialog.add(CancelPopup, {
            title: _t("Cancel order"),
            confirm: () => {
                this.router.navigate("default");
            },
        });
    }
}
