import { BaseOptionComponent } from "@html_builder/core/utils";

/**
 * Customize tab component for the Products Design Panel.
 * This component renders the full design panel content in the editor's customize tab.
 */
export class ProductsDesignPanelTab extends BaseOptionComponent {
    static template = "website_sale.ProductsDesignPanelTab";
    static components = {
        ...BaseOptionComponent.components,
    };
    static props = {
        onClose: Function,
        isShop: { type: Boolean, optional: true },
        label: { type: String, optional: true },
    };
    static defaultProps = {
        isShop: false,
        label: "Design",
    };

    setup() {
        super.setup();
    }
}
