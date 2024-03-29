/** @odoo-module */
/* global Carousel */

import { Component, onMounted, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { LanguagePopup } from "@pos_self_order/app/components/language_popup/language_popup";

export class LandingPage extends Component {
    static template = "pos_self_order.LandingPage";

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.carouselRef = useRef("carousel");
        this.activeSelected = false;
        this.carouselInterval = null;

        onWillStart(() => {
            if (this.selfOrder.config.self_ordering_mode === "kiosk") {
                this.selfOrder.orders = [];
                this.selfOrder.editedOrder = null;
            }
            this.selfOrder.rpcLoading = false;
        });

        onMounted(() => {
            if (this.selfOrder.config.self_ordering_image_home_ids.length > 1) {
                // used to init carousel after components mount / unmount
                const carousel = new Carousel(this.carouselRef.el);

                // prevent traceback when no image is set
                this.carouselInterval = setInterval(() => {
                    carousel.next();
                }, 5000);
            }
        });

        onWillUnmount(() => {
            clearInterval(this.carouselInterval);
        });
    }

    get currentLanguage() {
        return this.selfOrder.currentLanguage;
    }

    get languages() {
        return this.selfOrder.config.self_ordering_available_language_ids;
    }

    get activeImage() {
        if (!this.activeSelected) {
            this.activeSelected = true;
            return "active";
        }
        return "";
    }

    get draftOrder() {
        return this.selfOrder.orders.filter((o) => o.access_token && o.state === "draft");
    }

    hideBtn(link) {
        const arrayLink = link.url.split("/");
        const routeName = arrayLink[arrayLink.length - 1];

        if (routeName !== "products") {
            return;
        }

        return (
            this.draftOrder.length > 0 && this.selfOrder.config.self_ordering_pay_after === "each"
        );
    }

    clickMyOrder() {
        this.router.navigate(this.draftOrder.length > 0 ? "cart" : "orderHistory");
    }

    clickCustomLink(link) {
        const arrayLink = link.url.split("/");
        const routeName = arrayLink[arrayLink.length - 1];

        if (routeName !== "products") {
            this.router.customLink(link);
            return;
        }

        this.start();
    }

    start() {
        if (
            this.draftOrder.length > 0 &&
            this.selfOrder.config.self_ordering_pay_after === "each"
        ) {
            return;
        }

        if (
            this.selfOrder.config.self_ordering_takeaway &&
            this.selfOrder.currentOrder.take_away === null &&
            this.selfOrder.ordering
        ) {
            this.router.navigate("location");
        } else {
            this.router.navigate("product_list");
        }
    }

    openLanguages() {
        this.dialog.add(LanguagePopup);
    }

    showMyOrderBtn() {
        const ordersNotDraft = this.selfOrder.orders.find((o) => o.access_token);
        return this.selfOrder.ordering && ordersNotDraft;
    }
}
