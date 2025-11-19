import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Many2OneField, buildM2OFieldDescription } from '@web/views/fields/many2one/many2one_field';

export class PickupLocationMany2OneField extends Many2OneField {
    static template = 'delivery.PickupLocationField';

    async setup(){
        super.setup();
        this.orm = useService('orm');
        this.dialog = useService('dialog');
        this.action = useService('action');
        const partnerRecord = this.props.record.data[this.props.name];
        this.selectedLocationId = partnerRecord.pickup_location_data?.id.toString();
        if (!this.props.record.resId) {
            await this.props.record.save();
        }
        this.parentId = this.props.record.resId;
        this.parentModel = this.props.record.resModel;
    }

    async onSelectLocation(ev) {
        await this.props.record.save();
        this.dialog.add(LocationSelectorDialog, {
            parentModel: this.parentModel,
            parentId: this.parentId,
            zipCode: this.props.context.partner_zip_code || '',
            selectedLocationId: this.selectedLocationId,
            save: async location => {
                const jsonLocation = JSON.stringify(location);
                let action = await this.orm.call(this.parentModel, 'set_pickup_location', [this.parentId], {
                    pickup_location_data: jsonLocation,
                });
                if (action) {
                    this.action.doAction(action);
                } else {
                    this.action.loadState();
                }
            },
        });
    }

    /**
     * Whether the button to select a location is enabled.
     *
     * This allows overrides in others modules.
     *
     * @returns {Boolean}
     */
    isButtonDisabled() {
        return false;
    }
}

export const pickupLocationMany2OneField = {
    ...buildM2OFieldDescription(PickupLocationMany2OneField),

    relatedFields: [
        { name: "pickup_location_data" },
    ],
};

registry.category('fields').add('pickup_location_many2one', pickupLocationMany2OneField);
