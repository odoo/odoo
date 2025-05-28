import { useSubEnv } from '@odoo/owl';
import {
    ProductConfiguratorDialog
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';
import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';

patch(ProductConfiguratorDialog, {
    props: {
        ...ProductConfiguratorDialog.props,
        isFrontend: { type: Boolean, optional: true },
        options: {
            ...ProductConfiguratorDialog.props.options,
            shape: {
                ...ProductConfiguratorDialog.props.options.shape,
                isMainProductConfigurable: { type: Boolean, optional: true },
                isBuyNow: { type: Boolean, optional: true },
            },
        },
    },
});

patch(ProductConfiguratorDialog.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.props.isFrontend) {
            this.getValuesUrl = '/website_sale/product_configurator/get_values';
            this.createProductUrl = '/website_sale/product_configurator/create_product';
            this.updateCombinationUrl = '/website_sale/product_configurator/update_combination';
            this.getOptionalProductsUrl = '/website_sale/product_configurator/get_optional_products';
            this.title = _t("Configure");
        }

        useSubEnv({
            isFrontend: this.props.isFrontend,
            isMainProductConfigurable: this.props.options?.isMainProductConfigurable ?? true,
        });
    },

    /**
     * Check whether all selected products can be sold.
     *
     * @return {Boolean} - Whether all selected products can be sold.
     */
    canBeSold() {
        return this.state.products.every(p => p.can_be_sold);
    },

    /**
     * Check whether to show the "shop" buttons in the dialog footer.
     *
     * @return {Boolean} - Whether to show the "shop" buttons in the dialog footer.
     */
    showShopButtons() {
        return this.props.isFrontend && !this.props.edit;
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

});
