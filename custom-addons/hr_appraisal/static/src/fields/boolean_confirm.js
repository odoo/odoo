/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

import { CheckBox } from "@web/core/checkbox/checkbox";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    BooleanToggleField,
    booleanToggleField,
} from "@web/views/fields/boolean_toggle/boolean_toggle_field";

import { session } from '@web/session';

export class ConfirmCheckBox extends CheckBox {
    onClick(ev) {
        ev.preventDefault();

        if (ev.target.tagName !== "INPUT") {
            return;
        }
        this.props.onChange(ev.target.checked);
    }
}

export class BooleanToggleConfirm extends BooleanToggleField {
    setup() {
        super.setup();
        this.dialogService = useService('dialog');
    }

    onChange(value) {
        const record = this.props.record.data;
        const updateAndSave = () => {
            this.props.record.update({ [this.props.name]: value }, { save: true });
        };

        const isEmployee = record.employee_user_id && record.employee_user_id[0] === session.uid;
        if (record.is_manager && value && !isEmployee) {
            this.dialogService.add(ConfirmationDialog, {
                body: _t("The employee's feedback will be published without their consent. Do you really want to publish it? This action will be logged in the chatter."),
                confirm: updateAndSave,
                cancel: () => {},
            });

        }
        else {
            updateAndSave();
        }
    }
}
BooleanToggleConfirm.template = 'hr_appraisal.BooleanToggleConfirm';
BooleanToggleConfirm.components = { ConfirmCheckBox };

export const booleanToggleConfirm = {
    ...booleanToggleField,
    component: BooleanToggleConfirm,
};

registry.category("fields").add("boolean_toggle_confirm", booleanToggleConfirm);
