import {
    PickupLocationMany2OneField
} from '@delivery/js/pickup_location_many2one/pickup_location_many2one';
import { patch } from '@web/core/utils/patch';

patch(PickupLocationMany2OneField.prototype, {
    isButtonDisabled() {
        if (this.props.record.resModel === 'stock.picking') {
            return ['cancel', 'done'].includes(this.props.record.data.state);
        }
        return super.isButtonDisabled();
    }
});
