import { t, useProps } from "@odoo/owl";
import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";
import { _t } from "@web/core/l10n/translation";

export class ProductCatalogSaleOrderLine extends ProductCatalogOrderLine {
    deliveryProps = useProps({
        deliveredQty: t.number(),
    });

    get disableRemove() {
        return this.props.quantity === this.deliveryProps.deliveredQty;
    }

    get disabledButtonTooltip() {
        if (this.disableRemove) {
            return _t(
                "The ordered quantity cannot be decreased below the amount already delivered. Instead, create a return in your inventory."
            );
        }
        return super.disabledButtonTooltip;
    }
}
