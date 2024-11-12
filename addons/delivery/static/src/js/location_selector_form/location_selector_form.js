/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { LocationSelectorDialog } from "../location_selector/location_selector_dialog/location_selector_dialog";
import { rpc } from "@web/core/network/rpc";
import { onMounted } from "@odoo/owl"
import { useService } from "@web/core/utils/hooks";

export class LocationSelectorFormController extends FormController {    
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.action = useService("action");
        
        onMounted(async () => {
            this.dialog.closeAll();
            const rec = this.model.root.data;
            this.parentModel = rec.parent_model;
            this.parentId = rec.parent_id;
            this.zipCode = rec.zip_code;
            this.selectedLocationId = rec.selected_pickup_location;
            this.dialog.add(LocationSelectorDialog, {
                parentModel: this.parentModel,
                parentId: this.parentId,
                zipCode: this.zipCode,
                selectedLocationId: this.selectedLocationId,
                save: this.save.bind(this),
            });
        });
    }

    async save (location) {
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
    };
}

export const LocationSelectorFormView = {
    ...formView,
    Controller: LocationSelectorFormController,
}

registry.category("views").add("location_selector_form", LocationSelectorFormView);
