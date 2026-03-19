import { useSubEnv } from "@web/owl2/utils";
import { t } from "@odoo/owl";
import {
    ProductConfiguratorDialog,
    productConfiguratorDialogOptionsShape,
    productConfiguratorDialogProps,
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';
import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';

Object.assign(productConfiguratorDialogOptionsShape, {
    isMainProductConfigurable: t.boolean().optional(),
    isBuyNow: t.boolean().optional(),
});
Object.assign(productConfiguratorDialogProps, {
    isFrontend: t.boolean().optional(),
    // Rebuild the `options` entry so that it picks up the extended shape.
    options: t.object(productConfiguratorDialogOptionsShape).optional(),
});

patch(ProductConfiguratorDialog.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.props.isFrontend) {
            this.createProductUrl = '/website_sale/product_configurator/create_product';
            this.updateCombinationUrl = '/website_sale/product_configurator/update_combination';
            this.getOptionalProductsUrl = '/website_sale/product_configurator/get_optional_products';
            this.title = _t("Configure");
        }

        useSubEnv({
            isFrontend: this.props.isFrontend,
            isMainProductConfigurable: this.props.options?.isMainProductConfigurable ?? true,
            isQuantityAllowed: this._isQuantityInStock.bind(this),
        });
    },

    /**
     * Override of `sale` to limit the quantity to the stock availability
     */
    async _setQuantity(productTmplId, quantity) {
        const product = this._findProduct(productTmplId);
        if (!this._isQuantityInStock(product, quantity)) {
            quantity = product.free_qty;
        }
        return super._setQuantity(productTmplId, quantity)
    },

    /**
     * Check whether all selected products can be sold.
     *
     * @return {Boolean} - Whether all selected products can be sold.
     */
    canBeSold() {
        return this.state.products.every(p => p.can_be_sold && this._isQuantityInStock(p, p.quantity));
    },

    /**
     * Check whether to show the "shop" buttons in the dialog footer.
     *
     * @return {Boolean} - Whether to show the "shop" buttons in the dialog footer.
     */
    showShopButtons() {
        return this.props.isFrontend && !this.props.edit;
    },

    _handleUnitOfMeasureUpdate(product, combination, uomId) {
        super._handleUnitOfMeasureUpdate(...arguments);
        if (this.props.isFrontend && combination.strikethrough_price) {
            product.strikethrough_price = parseFloat(combination.strikethrough_price);
        }
    },

    get totalMessage() {
        if (this.env.isFrontend) {
            // To be translated, the title must be repeated here. Indeed, only
            // translations of "frontend modules" are fetched in the context of
            // website. The original definition of the title is in "sale", which
            // is not a frontend module.
            return _t("Total: %s", this.getFormattedTotal());
        }
        return super.totalMessage(...arguments);
    },

    /**
     * Check whether the provided product quantity can be added to the cart.
     *
     * @param {Object} product - The provided product.
     * @param {Number} quantity - The new quantity of the product.
     * @return {Boolean} - Whether the provided product quantity can be added to the cart.
     */
    _isQuantityInStock(product, quantity) {
        // `product` may be a props object, which always exposes every declared key (including the
        // optional `free_qty`), so the presence of the key can't be used to detect stock tracking.
        return product.free_qty === undefined || product.free_qty >= quantity;
    },

});
