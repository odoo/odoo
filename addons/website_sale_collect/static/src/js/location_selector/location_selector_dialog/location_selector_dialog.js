import { rpc } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';

patch(LocationSelectorDialog, {
    props: {
        ...LocationSelectorDialog.props,
        productId: { type: Number, optional: true },
        isProductPage: { type: Boolean, optional: true },
    },
});

patch(LocationSelectorDialog.prototype, {
    _getLocationsParams() {
        let params = super._getLocationsParams(...arguments);
        if (this.props.isProductPage) {
            params.product_id = this.props.productId;
        }
        return params
    },
});
