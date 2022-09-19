/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';

patch(SaleOrderLineProductField.prototype, 'sale_product_configurator', {

    setup() {
        this._super(...arguments);

        this.rpc = useService("rpc");
    },

    async _onFieldUpdate() {
        this._super(...arguments);
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data[this.props.name][0]],
        );
        if(result && result.product_id){
            this.props.record.update({
                'product_id': [result.product_id.id, 'whatever'],
            });
            if (result.has_optional_products) {
                // TODO
                // need ability to add records on x2m
                // from field widget
                this._openProductConfigurator('options');
            }
        } else {
            if (!result.add_mode || result.add_mode === 'configurator') {
                this._openProductConfigurator('add');
            } else {
                this._openGridConfigurator();
            }
        }
    },

    _editProductConfiguration() {
        this._super(...arguments);
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfigurator('edit');
            // TODO matrix/grid
            // TODO add related field on product_add_mode ?
            // to use in matrix
        }
    },

    get isConfigurableTemplate() {
        return this._super(...arguments) || this.props.record.data.is_configurable_product;
    },

    async _openProductConfigurator(mode) {
        const saleOrderRecord = this.props.record.model.root;
        debugger;
        const $modal = await this.rpc(
            "/sale_product_configurator/configure",
            {
                'product_template_id': this.props.record.data['product_template_id'][0],
                'pricelist_id': saleOrderRecord.data['pricelist_id'] ? saleOrderRecord.data['pricelist_id'][0] : false, // HOW to get this from SO ?
                // TODO test when line is setup
                // qty ?
                // 'product_template_attribute_value_ids': '',
                // 'product_no_variant_attribute_value_ids': '',
                // TODO custom attributes ?
            },
        );
    },
});
