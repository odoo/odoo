/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import {
  booleanField,
  BooleanField,
} from "@web/views/fields/boolean/boolean_field";


export class ConfirmCheckBox extends CheckBox {
    onClick(ev) {
        ev.preventDefault();
        if (ev.target.tagName !== "INPUT") {
            return;
        }
        this.props.onChange(ev.target.checked);
    }
}

export class BooleanTrackingField extends BooleanField {
    static template = "stock.TrackingBooleanConfirm";
    static components = { ConfirmCheckBox };

    setup() {
        super.setup();
        this.dialogService = useService('dialog');
    }

    /**
     * @override
     */
    async onChange(newValue) {
        const { is_storable, has_move_line_ids, qty_available } = this.props.record.data;
        const showConfirmationDialog = (title, body, confirmLabel) => {
            return this.dialogService.add(ConfirmationDialog, {
                title: _t(title),
                body: _t(body),
                confirm: () => {
                    this.props.record.update({ [this.props.name]: newValue }, { save: true });
                },
                confirmLabel: _t(confirmLabel),
                cancel: () => {},
                cancelLabel: _t("Discard"),
            });
        };
        if (has_move_line_ids && !is_storable && newValue) {
            return showConfirmationDialog(
                "Start Tracking",
                "If you have this product in stock and your transfers require existing lot/serial number, you may run issues.\nAdjust your inventory to precise serials/lots in stock if necessary",
                "Track Product"
            );
        } else if (qty_available && is_storable && !newValue) {
            return showConfirmationDialog(
                "Confirmation",
                "Are you sure you want to stop tracking this product?\nAll existing tracability will be lost",
                "Yes"
            );
        }
        super.onChange(...arguments);
    }
}

export const booleanTrackingField = {
    ...booleanField,
    component: BooleanTrackingField,
};

registry.category("fields").add("boolean_tracking", booleanTrackingField);
