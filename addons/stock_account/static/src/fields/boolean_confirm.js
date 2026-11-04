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
    static template = "stock_account.BooleanToggleConfirm";
    static components = { ConfirmCheckBox };

    setup() {
        super.setup();
        this.dialogService = useService('dialog');
    }

    onChange(value) {
        const record = this.props.record.data;
        const updateAndSave = () => {
            this.props.record.update({ [this.props.name]: value }, { save: true });
        };

        if (record.lot_valuated && !value) {
            this.dialogService.add(ConfirmationDialog, {
                body: _t("This operation might lead in a loss of data. Valuation will be identical for all lots/SN. Do you want to proceed ? "),
                confirm: updateAndSave,
                cancel: () => {},
            });

        }
        else {
            updateAndSave();
        }
    }
}

export const booleanToggleConfirm = {
    ...booleanToggleField,
    component: BooleanToggleConfirm,
};

registry.category("fields").add("confirm_boolean", booleanToggleConfirm);
