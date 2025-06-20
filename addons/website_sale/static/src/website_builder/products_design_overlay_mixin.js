import { useState } from "@odoo/owl";
import { ProductsDesignOverlay } from "@website_sale/website_builder/products_design_overlay";

/**
 * Mixin function to add ProductsDesignOverlay functionality to components
 */
export function ProductsDesignOverlayMixin(BaseClass) {
    return class extends BaseClass {
        static components = {
            ...BaseClass.components,
            ProductsDesignOverlay
        };

        setup() {
            super.setup();
            // Ensure state exists and add overlay visibility
            if (!this.state) {
                this.state = useState({ overlayVisible: false });
            } else {
                this.state.overlayVisible = false;
            }
            console.log(this.state.overlayVisible)
        }

        openDesignOverlay() {
            this.state.overlayVisible = true;
        }

        closeDesignOverlay() {
            this.state.overlayVisible = false;
        }
    };
}
