/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class TrackingSelection extends SelectionField {
    setup() {
        super.setup();
        this.dialogService = useService('dialog');
    }

    onChange(ev) {
        const value = JSON.parse(ev.target.value);
        const { tracking, qty_available } = this.props.record.data;

        const showConfirmationDialog = (title, body, confirmLabel) => {
            return this.dialogService.add(ConfirmationDialog, {
                title: _t(title),
                body: _t(body),
                confirm: () => {
                    this.props.record.update({ [this.props.name]: value }, { save: true });
                },
                confirmLabel: _t(confirmLabel),
                cancel: () => { this.props.record.discard() },
                cancelLabel: _t("Discard"),
            });
        };

        if (qty_available) {
            if (tracking === 'none' && value !== 'none') {
                return showConfirmationDialog(
                    "Start Tracking by Serial/Lot",
                    "If you have this product in stock and your transfers require existing lot/serial number, you may run issues.\nAdjust your inventory to precise serials/lots in stock if necessary",
                    "Track by Serial/Lot"
                );
            } else if (tracking !== 'none' && value === 'none') {
                return showConfirmationDialog(
                    "Confirmation",
                    "Are you sure you want to stop tracking this product by lot/serial?\nAll existing tracability will be lost",
                    "Yes"
                );
            } else if (tracking === 'lot' && value === 'serial') {
                return showConfirmationDialog(
                    "Track by Serial",
                    "All lots will be lost. If you have this product in stock and your transfers require existing lot/serial number, you may run issues.\nAdjust your inventory to precise serials in stock if necessary",
                    "Track by Serial"
                );
            }
            return this.props.record.update({ [this.props.name]: value }, { save: true });
        }
        super.onChange(ev);
    }
}

export const trackingSelection = {
    ...selectionField,
    component: TrackingSelection,
};

registry.category("fields").add("tracking_selection", trackingSelection);
