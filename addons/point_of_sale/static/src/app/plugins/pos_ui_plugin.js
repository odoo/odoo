import { signal, computed } from "@odoo/owl";
import { services } from "@web/core/services";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { SIZES } from "@web/core/ui/ui_utils";

export class PosUiPlugin extends UIPlugin {
    static id = UIPlugin.id; // replace the core instance instead of creating a second one
    static sequence = 1; // must start before anything calls usePlugin(UIPlugin)

    cameraScan = signal(false);
    productScreenMobileDisplayMode = signal("product"); // "cart", "product"
    ticketScreenMobileDisplayMode = signal("order"); // "cart", "order"
    isMedium = computed(() => this.size() < SIZES.MD);

    get isProductScreenOnCart() {
        return this.productScreenMobileDisplayMode() === "cart";
    }

    get isProductScreenOnProduct() {
        return this.productScreenMobileDisplayMode() === "product";
    }

    get isTicketScreenOnCart() {
        return this.ticketScreenMobileDisplayMode() === "cart";
    }

    get isTicketScreenOnOrder() {
        return this.ticketScreenMobileDisplayMode() === "order";
    }

    toggleProductMobileScreenDisplayMode() {
        this.productScreenMobileDisplayMode.set(
            this.productScreenMobileDisplayMode() === "cart" ? "product" : "cart"
        );
    }

    toggleTicketScreenMobileDisplayMode() {
        this.ticketScreenMobileDisplayMode.set(
            this.ticketScreenMobileDisplayMode() === "cart" ? "order" : "cart"
        );
    }

    toggleCameraScan() {
        this.cameraScan.set(!this.cameraScan());
    }

    stopCameraScan() {
        this.cameraScan.set(false);
    }

    startCameraScan() {
        this.cameraScan.set(true);
    }
}

services.delete(UIPlugin);
services.add(PosUiPlugin);
