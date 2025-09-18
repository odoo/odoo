// @ts-check

/** @module @web/views/settings/fields/upgrade_boolean_field - Boolean field for settings that shows an Enterprise upgrade dialog when checked */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BooleanField, booleanField } from "@web/fields/basic/boolean/boolean_field";

import { UpgradeDialog } from "./upgrade_dialog";
/**
 *  The upgrade boolean field is intended to be used in config settings.
 *  When checked, an upgrade popup is showed to the user.
 */

export class UpgradeBooleanField extends BooleanField {
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
                        this.props.record.update({ [this.props.name]: false });
                    },
                },
            );
        } else {
            super.onChange(/** @type {any} */ (newValue));
        }
    }
}

export const upgradeBooleanField = {
    ...booleanField,
    component: UpgradeBooleanField,
    additionalClasses: [...(booleanField.additionalClasses || []), "o_field_boolean"],
};

registry.category("fields").add("upgrade_boolean", upgradeBooleanField);
