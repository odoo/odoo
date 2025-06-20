import { Component } from "@odoo/owl";

export class ProductsDesignOverlay extends Component {
    static template = "website_sale.ProductsDesignOverlay";
    static props = {
        isVisible: { type: Boolean },
        slots: { type: Object, optional: true },
    };

    static defaultProps = {
        isVisible: false,
    };

    hide() {
        // Find parent component and call its closse method
        let current = this.__owl__.parent;
        while (current) {
            if (current.component.closeDesignOverlay) {
                current.component.closeDesignOverlay();
                return;
            }
            current = current.parent;
        }
    }

    onBackdropClick(ev) {
        if (ev.target === ev.currentTarget) {
            this.hide();
        }
    }
}
