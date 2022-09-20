/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { ProductConfiguratorModal } from "@sale_product_configurator/js/product_configurator_modal";
import {
    selectOrCreateProduct,
    getSelectedVariantValues,
    getNoVariantAttributeValues,
} from "sale.VariantMixin";


patch(SaleOrderLineProductField.prototype, 'sale_product_configurator', {

    // TODO
    // 2) autofocus on first attribute in configurator
    //      unable to enter by hand custom values bc of it
    // 3) wizard opened when the variant is chosen in the 'Product Variant' field
    // 4) matrix

    _editProductConfiguration() {
        this._super(...arguments);
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfigurator('edit');
            // TODO matrix/grid
            // TODO add related field on product_add_mode ?
            // to use in matrix
        }
    },

    async _openGridConfigurator() {
        debugger;
    },
});
