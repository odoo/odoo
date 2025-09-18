import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { SelectionField, selectionField } from "@web/fields/selection/selection/selection_field";
import { UpgradeDialog } from "@web/views/settings/fields/upgrade_dialog";
/**
 *  The upgrade selection field is intended to be used in config settings.
 *  When selection changed, an upgrade popup is showed to the user.
 */

export class UpgradeSelectionField extends SelectionField {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.isEnterprise = odoo.info && odoo.info.isEnterprise;
    }

    async onChange(newValue) {
        if (!this.isEnterprise) {
            this.dialogService.add(
                UpgradeDialog,
                {},
                {
                    onClose: () => {
                        newValue.target.value = '"meal"';
                    },
                },
            );
        } else {
            super.onChange(...arguments);
        }
    }
}

export const upgradeSelectionField = {
    ...selectionField,
    component: UpgradeSelectionField,
    additionalClasses: [
        ...(selectionField.additionalClasses || []),
        "o_field_selection",
    ],
};

registry.category("fields").add("upgrade_selection", upgradeSelectionField);
