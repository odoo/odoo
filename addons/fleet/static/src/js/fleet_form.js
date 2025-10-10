import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class FleetFormController extends FormController {
    /**
     * @override
     **/
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        menuItems.archive.callback = () => {
            const dialogProps = {
                title: _t("Archive Vehicle"),
                body: _t(
                    "All services and contracts linked to this vehicle will also be archived.\nAre you sure you want to proceed?"
                ),
                confirmLabel: _t("Archive Vehicle & Contracts"),
                confirm: () => this.model.root.archive(),
                cancel: () => {},
            };
            this.dialogService.add(ConfirmationDialog, dialogProps);
        };
        return menuItems;
    }
}

export const fleetFormView = {
    ...formView,
    Controller: FleetFormController,
};

registry.category("views").add("fleet_form", fleetFormView);
