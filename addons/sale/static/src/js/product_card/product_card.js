import { Component } from '@odoo/owl';
import { BadgeExtraPrice } from '../badge_extra_price/badge_extra_price';
import { ProductProduct } from '../models/product_product';

export class ProductCard extends Component {
    static template = 'sale.ProductCard';
    static components = { BadgeExtraPrice };
    static props = {
        product: ProductProduct,
        extraPrice: { type: Number, optional: true },
        onClick: Function,
        isSelected: { type: Boolean, optional: true },
    };

    /**
     * Check whether the provided PTAL should be shown in this card.
     *
     * @param {ProductTemplateAttributeLine} ptal The PTAL to check.
     * @return {Boolean} Whether to show the PTAL.
     */
    shouldShowPtal(ptal) {
        return ptal.hasSelectedCustomPtav || ptal.create_variant === 'no_variant';
    }
}
