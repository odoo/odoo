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
    async _getLocations(zip) {
         if (this.props.isProductPage) {
             return rpc(this.getLocationUrl, { zip_code: zip, product_id: this.props.productId });
         }
        else {
            return super._getLocations(...arguments);
         }
    },
});
