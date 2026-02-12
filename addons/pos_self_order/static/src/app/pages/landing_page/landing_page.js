import { Component, onWillStart } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { LanguagePopup } from "@pos_self_order/app/components/language_popup/language_popup";
import { useCarousel } from "@pos_self_order/app/utils/carousel_hook";

export class LandingPage extends Component {
    static template = "pos_self_order.LandingPage";
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.activeSelected = false;

        onWillStart(() => {
            if (this.selfOrder.config.self_ordering_mode === "kiosk") {
                const orders = this.selfOrder.models["pos.order"].getAll();
                for (const order of orders) {
                    order.delete();
                }
                this.selfOrder.selectedOrderUuid = null;
            }
            this.selfOrder.rpcLoading = false;
        });

        if (this.selfOrder.config._self_ordering_image_home_ids.length > 1) {
            useCarousel("carousel", 5);
        }
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
        return this.selfOrder.models["pos.order"].filter(
            (o) => o.access_token && o.state === "draft"
        );
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
        if (this.selfOrder.hasPresets() && !this.selfOrder.currentOrder.preset_id) {
            this.router.navigate("location");
        } else {
            this.router.navigate("product_list");
        }
    }

    openLanguages() {
        this.dialog.add(LanguagePopup);
    }

    showMyOrderBtn() {
        const ordersNotDraft = this.selfOrder.models["pos.order"].find((o) => o.access_token);
        return this.selfOrder.ordering && ordersNotDraft;
    }
}
