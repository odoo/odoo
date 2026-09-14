/** @odoo-module native */
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { FormController, formView } from "@web/views/form";

export class FleetFormController extends FormController {
    /**
     * @override
     **/
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        if (menuItems.archive) {
            menuItems.archive.callback = () =>
                this.archiveRecord({
                    body: _t(
                        "Every service and contract of this vehicle will be considered as archived. Are you sure that you want to archive this record?",
                    ),
                });
        }
        return menuItems;
    }
}

export const fleetFormView = {
    ...formView,
    Controller: FleetFormController,
};

registry.category("views").add("fleet_form", fleetFormView);
