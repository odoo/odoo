import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class StockLocationFormController extends FormController {
    // Navigating away shouldn't stop the record from being saved, and should be
    // interpreted as confirming the dialog (that never got to launch).
    async beforeLeave() {
        this.isLeaving = true;
        try {
            return await super.beforeLeave(...arguments);
        } finally {
            this.isLeaving = false;
        }
    }

    async onWillSaveRecord(record) {
        if ((await super.onWillSaveRecord(...arguments)) === false) {
            return false;
        }

        this.parentToConvert = false;
        const parent = record.data.location_id;
        if (record.resId || !parent || this.isLeaving) {
            return true;
        }
        const [[{ usage }], hasSublocations] = await Promise.all([
            this.orm.read("stock.location", [parent.id], ["usage"]),
            this.orm.call("stock.location", "has_sublocations", [[parent.id]]),
        ]);
        if (usage !== "internal" || hasSublocations) {
            return true;
        }

        return new Promise((resolve) => {
            this.dialogService.add(
                ConfirmationDialog,
                {
                    title: _t("Where to store products?"),
                    body: _t(
                        "%(name)s now has sublocations.\nKeep storing in %(name)s itself, or only in its sublocations?",
                        { name: parent.display_name }
                    ),
                    confirm: () => resolve(true),
                    confirmLabel: _t("Both"),
                    cancel: () => {
                        // The write waits until the child is saved.
                        this.parentToConvert = parent.id;
                        resolve(true);
                    },
                    cancelLabel: _t("Sublocations only"),
                    dismiss: () => resolve(false),
                },
                { onClose: () => resolve(false) }
            );
        });
    }

    async onRecordSaved() {
        await super.onRecordSaved(...arguments);
        if (this.parentToConvert) {
            const parentId = this.parentToConvert;
            this.parentToConvert = false;
            // Do not await here. The sublocation record is already created.
            // We expect a UserError to be thrown if the parent turns out to
            // have existing quants. Awaiting would make the error throw midwrite
            // before the form can reload.
            this.orm.write("stock.location", [parentId], { usage: "view" });
        }
    }
}

export const stockLocationFormView = {
    ...formView,
    Controller: StockLocationFormController,
};

registry.category("views").add("stock_location_form", stockLocationFormView);
