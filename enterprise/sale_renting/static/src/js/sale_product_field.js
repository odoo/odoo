/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { serializeDateTime } from "@web/core/l10n/dates";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';

patch(SaleOrderLineProductField.prototype, {
    _getAdditionalRpcParams() {
        const params = super._getAdditionalRpcParams();
        const saleOrder = this.props.record.model.root;
        if (saleOrder.data.rental_start_date && saleOrder.data.rental_return_date) {
            params.start_date = serializeDateTime(saleOrder.data.rental_start_date);
            params.end_date = serializeDateTime(saleOrder.data.rental_return_date);
        }
        return params;
    },

    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();
        const saleOrder = this.props.record.model.root;
        if (saleOrder.data.rental_start_date && saleOrder.data.rental_return_date) {
            props.rentalStartDate = serializeDateTime(saleOrder.data.rental_start_date);
            props.rentalEndDate = serializeDateTime(saleOrder.data.rental_return_date);
        }
        return props;
    },
});
