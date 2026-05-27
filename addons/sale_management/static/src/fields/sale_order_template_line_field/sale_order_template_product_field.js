import { registry } from '@web/core/registry';
import { serializeDateTime, today } from '@web/core/l10n/dates';
import {
    SaleOrderLineProductField,
    saleOrderLineProductField,
} from '@sale/js/sale_product_field/sale_product_field';

export class SaleOrderTemplateLineProductField extends SaleOrderLineProductField {
    get isProductClickable() {
        return false;
    }

    _getOrderLines() {
        return this.props.record.model.root.data.sale_order_template_line_ids;
    }

    _getSoDate() {
        return serializeDateTime(today());
    }
}

export const saleOrderTemplateProductField = {
    ...saleOrderLineProductField,
    component: SaleOrderTemplateLineProductField,
    fieldDependencies: [
        { name: 'product_uom_id', type: 'many2one' },
        { name: 'product_uom_qty', type: 'float' },
        { name: 'is_configurable_product', type: 'boolean' },
        { name: 'product_template_attribute_value_ids', type: 'many2many' },
        { name: 'currency_id', type: 'many2one' },
    ],
};

registry.category('fields').add('sotl_product_many2one', saleOrderTemplateProductField);
