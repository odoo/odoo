import { Component, useRef } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { LanguageSelector } from "@pos_self_order/app/components/language_selector/language_selector";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";

export class EatingLocationPage extends Component {
    static template = "pos_self_order.EatingLocationPage";
    static props = {};
    static components = { LanguageSelector };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.scrollContainerRef = useRef("scrollContainer");
        this.scrollShadow = useScrollShadow(this.scrollContainerRef);
    }

    onClickBack() {
        this.router.navigate("default");
    }

    selectPreset(preset) {
        this.selfOrder.currentOrder.setPreset(preset);
        this.router.navigate("product_list");
    }

    get presets() {
        return this.selfOrder.models["pos.preset"].getAll();
    }

    get backgroundImage() {
        const bgImage = this.selfOrder.config._self_ordering_image_background_ids[0];
        if (bgImage) {
            return `url(data:image/png;base64,${bgImage.data})`;
        }
        return "none";
    }
}
