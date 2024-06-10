/** @odoo-module **/

import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';
import { patch } from '@web/core/utils/patch';

patch(LocationSelectorDialog, {
    props: {
        ...LocationSelectorDialog.props,
        orderId: { type: Number, optional: true },
        isFrontend: { type: Boolean, optional: true },
    },
});

patch(LocationSelectorDialog.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.props.isFrontend) {
            this.getLocationUrl = '/website_sale/get_pickup_locations';
        }
    },
});
