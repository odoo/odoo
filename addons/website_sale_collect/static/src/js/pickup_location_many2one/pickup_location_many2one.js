import { patch } from "@web/core/utils/patch";

import {
    PickupLocationMany2OneField
} from "@website_sale_stock/js/pickup_location_many2one/pickup_location_many2one";

patch(PickupLocationMany2OneField.prototype, {
    _getLocationSelectorDialogProps() {
        return {
            ...super._getLocationSelectorDialogProps(),
            deliveryMethodType: this.props.record.data.delivery_type,
        }
    }
});
