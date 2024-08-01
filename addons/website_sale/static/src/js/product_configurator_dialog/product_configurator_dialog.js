/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { useSubEnv } from '@odoo/owl';
import {
    ProductConfiguratorDialog
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';

patch(ProductConfiguratorDialog, {
    props: {
        ...ProductConfiguratorDialog.props,
        isFrontend: { type: Boolean, optional: true },
        options: {
            ...ProductConfiguratorDialog.props.options,
            shape: {
                ...ProductConfiguratorDialog.props.options.shape,
                isMainProductConfigurable: { type: Boolean, optional: true },
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
});
