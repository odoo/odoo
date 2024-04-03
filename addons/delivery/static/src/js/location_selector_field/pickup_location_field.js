import { buildM2OFieldDescription, extractM2OFieldProps, Many2OneField } from '@web/views/fields/many2one/many2one_field';
import { computeM2OProps, Many2One } from '@web/views/fields/many2one/many2one';
import { registry } from '@web/core/registry';
import { Component } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';

export class PickupLocationField extends Component {
    static template = 'delivery.PickupLocationField';
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    async setup(){
        super.setup();
        this.orm = useService('orm');
        this.dialog = useService('dialog');
        this.action = useService('action');
        const record = this.props.record.data;
        const partner = await this.orm.searchRead('res.partner', [['id', '=', record.partner_id.id]], ['zip']);
        const deliveryAddress = await this.orm.searchRead('res.partner', [['id', '=', record[this.props.name]?.id]], ['pickup_location_data']);
        this.selectedLocationId = deliveryAddress[0]?.pickup_location_data?.id?.toString();
        this.zipCode = partner[0]?.zip || '';
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
            zipCode: this.zipCode,
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

    isButtonDisabled() {
        return this.props.record.resModel === 'stock.picking' && ['cancel', 'done'].includes(this.props.record.data.state);
    }

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            relation: 'res.partner',
        };
    }
    
}

export const pickupLocationField = {
    ...buildM2OFieldDescription(PickupLocationField),
    extractProps(fieldInfo, dynamicInfo) {
        const props = extractM2OFieldProps(fieldInfo, dynamicInfo);
        props.readonly = true;
        return props;
    },
};

registry.category('fields').add('pickup_location_many2one', pickupLocationField);
