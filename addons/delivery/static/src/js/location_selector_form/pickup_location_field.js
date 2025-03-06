import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';


export class PickupLocationField extends Many2OneField {
    static template = "delivery.PickupLocationField";

    async setup(){
        super.setup();
        const record = this.props.record.data;
        const partner = await this.orm.searchRead("res.partner", [["id", "=", record.partner_id[0]]], ["zip"]);
        const deliveryAddress = await this.orm.searchRead("res.partner", [["id", "=", record.delivery_address_id?.[0]]], ["location_data"]);
        this.selectedLocationId = deliveryAddress?.[0]?.location_data?.id?.toString();
        this.zipCode = partner[0].zip;
        if (!this.props.record.resId) {
            await this.props.record.save();
        }
        this.parentId = this.props.record.resId;
        this.parentModel = this.props.record.resModel;
    }
    
    onSelectLocation(ev) {
        this.dialog.add(LocationSelectorDialog, {
            parentModel: this.parentModel,
            parentId: this.parentId,
            zipCode: this.zipCode,
            selectedLocationId: this.selectedLocationId,
            save: async location => {
                const jsonLocation = JSON.stringify(location);
                let action = await rpc('/delivery/set_pickup_location', {
                    pickup_location_data: jsonLocation,
                    res_model: this.parentModel,
                    res_id: this.parentId
                });
                if (action) {
                    this.action.doAction(action);
                } else {
                    this.action.loadState();
                }
            },
        });
    }
}

export const pickupLocationField = {
    ...many2OneField,
    component: PickupLocationField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneField.extractProps(fieldInfo, dynamicInfo);
        props.readonly = true;
        return props;
    },
};

registry.category("fields").add("pickup_location_many2one", pickupLocationField);
