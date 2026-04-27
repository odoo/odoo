/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import {
    ProductConfiguratorDialog
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';

patch(ProductConfiguratorDialog, {
    props: {
        ...ProductConfiguratorDialog.props,
        rentalStartDate: { type: String, optional: true },
        rentalEndDate: { type: String, optional: true },
    },
});

patch(ProductConfiguratorDialog.prototype, {
    _getAdditionalRpcParams() {
        const params = super._getAdditionalRpcParams();
        if (this.props.rentalStartDate && this.props.rentalEndDate) {
            params.start_date = this.props.rentalStartDate;
            params.end_date = this.props.rentalEndDate;
        }
        return params;
    },
});
