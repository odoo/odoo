import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField
} from "@web/views/fields/many2one/many2one_field";
import { Many2One } from "@web/views/fields/many2one/many2one";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    LocationSelectorDialog
} from "@website_sale_stock/js/location_selector/location_selector_dialog/location_selector_dialog";


export class PickupLocationMany2OneField extends Many2OneField {
    static template = "website_sale_stock.PickupLocationField";
    static components = {Many2One};
    static props = {...Many2OneField.props};

    async setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        if (!this.props.record.resId) {
            await this.props.record.save();
        }
    }

    async onSelectLocation(ev) {
        await this.props.record.save();
        this.dialog.add(LocationSelectorDialog, {
            ...this._getLocationSelectorDialogProps(),
        });
    }

    /**
     * Returns params for the location selector dialog.
     *
     * @returns {Object}
     * @private
     */
    _getLocationSelectorDialogProps() {
        return {
            deliveryMethodId: this.carrierId,
            countryId: this.countryId,
            zipCode: this.zipCode || "",
            selectedLocationId: this.selectedLocationId,
            save: async location => {
                const jsonLocation = JSON.stringify(location);
                await this.orm.call(
                    this.parentModel, "set_pickup_location", [[this.parentId], jsonLocation]
                );
                await this.props.record.load();
            },
        }
    }

    /**
     * Hook to override in other modules.
     *
     * @returns {Boolean} - Whether the location selection is allowed.
     */
    isButtonDisabled() {
        if (this.props.record.resModel === "stock.picking") {
            return ["cancel", "done"].includes(this.props.record.data.state);
        }
        return false;
    }

    get partnerRecord() {
        return this.props.record.data[this.props.name];
    }

    get selectedLocationId() {
        return this.partnerRecord.pickup_location_data?.id?.toString();
    }

    get zipCode() {
        return this.partnerRecord.zip;
    }

    get countryId() {
        return this.partnerRecord.country_id;
    }

    get parentId() {
        return this.props.record.resId;
    }

    get parentModel() {
        return this.props.record.resModel;
    }

    get carrierId() {
        return this.props.record.data.carrier_id?.id;
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
        { name: "pickup_location_data" },
        { name: "zip" },
        { name: "country_id" },
    ]
};

registry.category("fields").add("pickup_location_many2one", pickupLocationField);
