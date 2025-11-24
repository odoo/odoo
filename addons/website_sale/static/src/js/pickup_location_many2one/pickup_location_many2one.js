import { buildM2OFieldDescription, extractM2OFieldProps, Many2OneField } from '@web/views/fields/many2one/many2one_field';
import { Many2One } from '@web/views/fields/many2one/many2one';
import { registry } from '@web/core/registry';
import { onWillStart, onWillUpdateProps, useState } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import {
    LocationSelectorDialog
} from '@website_sale/js/location_selector/location_selector_dialog/location_selector_dialog';

export class PickupLocationMany2OneField extends Many2OneField {
    static template = 'website_sale.PickupLocationField';
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    async setup() {
        super.setup();
        this.orm = useService('orm');
        this.dialog = useService('dialog');
        this.action = useService('action');
        this.state = useState({
            isLoading: false,
            inapplicableDeliveryMethod: false,
        });
        onWillStart(() => this.checkCarrierApplicability());
        onWillUpdateProps((nextProps) => {
            if (nextProps.record !== this.props.record) {
                return this.checkCarrierApplicability(nextProps);
            }
        });

        if (!this.props.record.resId) {
            await this.props.record.save();
        }
    }

    get selectedLocationId() {
        const partnerRecord = this.props.record.data[this.props.name];
        return partnerRecord.pickup_location_data?.id?.toString();
    }

    get parentId() {
        return this.props.record.resId;
    }

    get parentModel() {
        return this.props.record.resModel;
    }

    async checkCarrierApplicability(props = this.props) {
        const record = props.record;
        const orderId = record.resModel === "sale.order" ? record.resId : record.data.order_id.id;
        this.state.isLoading = true;
        if (record.data.carrier_id) {
            const rateData = await this.orm.call("delivery.carrier", "rate_shipment_for_order", [record.data.carrier_id.id, orderId]);
            this.state.isLoading = false;
            if (!rateData.success) {
                this.state.inapplicableDeliveryMethod = true;
            }
        }
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

export const pickupLocationField = {
    ...buildM2OFieldDescription(PickupLocationMany2OneField),
    extractProps(fieldInfo, dynamicInfo) {
        const props = extractM2OFieldProps(fieldInfo, dynamicInfo);
        props.readonly = true;
        return props;
    },
    relatedFields: [
        { name: "pickup_location_data" }
    ]
};

registry.category('fields').add('pickup_location_many2one', pickupLocationField);
