import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { patch } from '@web/core/utils/patch';

patch(SaleOrderLineProductField.prototype, {
    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();

        const isOptionalLine = this.env.shouldCollapse(this.props.record, 'is_optional');
        props.options = {
            showQuantity: !isOptionalLine,
            showPrice: !isOptionalLine,
        };

        return props;
    },

    _prepareNewLineData(line, product) {
        const data = super._prepareNewLineData(line, product);
        if (this.env.shouldCollapse(line, 'is_optional')) {
            data.quantity = 0;
        }
        return data;
    }
});
