import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { patch } from '@web/core/utils/patch';

patch(SaleOrderLineProductField.prototype, {
    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();
        const parentRecord = this.props.record._parentRecord;
        const isOptionalLine = parentRecord
            ? this.env.shouldCollapse(this.props.record, 'is_optional')
            : false;

        props.options = {
            showQuantity: !isOptionalLine,
            showPrice: !isOptionalLine,
        };

        return props;
    },

    _prepareNewLineData(line, product) {
        const data = super._prepareNewLineData(line, product);
        const parentRecord = line._parentRecord;
        if (parentRecord && this.env.shouldCollapse(line, 'is_optional')) {
            data.quantity = 0;
        }
        return data;
    }
});
