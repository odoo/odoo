import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import { formView } from "@web/views/form/form_view";


class ProductTemplateFormRecord extends formView.Model.Record {
    _update(changes) {
        const { tracking = false, is_storable } = changes;
        const { qty_available, has_move_line_ids, tracking: product_tracking } = this.data;
        const showTrackingDialog = (title, body, confirmLabel) => {
            return this.model.dialog.add(ConfirmationDialog, {
                title: _t(title),
                body: _t(body),
                confirm: async() => {
                    this._applyChanges(changes)
                    await this.save();
                },
                confirmLabel: _t(confirmLabel),
                cancel: () => {
                    const undoChanges = this._applyChanges(changes);
                    undoChanges();
                },
                cancelLabel: _t("Discard"),
            });
        };
        if ((tracking && qty_available) ||  (is_storable !== undefined)) {
            if (product_tracking === 'none' && tracking && tracking !== 'none') {
                return showTrackingDialog(
                    "Start Tracking by Serial/Lot",
                    "If you have this product in stock and your transfers require existing lot/serial number, you may run into issues. Adjust your inventory to precise serials/lots in stock if necessary",
                    "Track by Serial/Lot"
                );
            } else if ((product_tracking !== 'none' && tracking === 'none') || (is_storable !== undefined && qty_available && !is_storable)) {
                return showTrackingDialog(
                    "Stop Tracking",
                    "Are you sure you want to stop tracking this product by lot/serial? All existing traceability will be lost",
                    "Yes"
                );
            } else if (product_tracking === 'lot' && tracking === 'serial') {
                return showTrackingDialog(
                    "Track by Serial",
                    "All lots will be lost. If you have this product in stock and your transfers require existing lot/serial number, you may run into issues. Adjust your inventory to precise serials in stock if necessary",
                    "Track by Serial"
                );
            } else if (is_storable !== undefined && has_move_line_ids && is_storable) {
                return showTrackingDialog(
                    "Start Tracking",
                    "If you have this product in stock and your transfers require existing lot/serial number, you may run issues.\nAdjust your inventory to precise serials/lots in stock if necessary",
                    "Track Product"
                );
            }
        }
        return super._update(...arguments);
    }
}

class ProductTemplateFormModel extends formView.Model {
    static Record = ProductTemplateFormRecord;
}

registry.category("views").add("product_template_form", {
    ...formView,
    Model: ProductTemplateFormModel,
});
