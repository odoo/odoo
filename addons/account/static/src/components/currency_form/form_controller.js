/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class CurrencyFormController extends FormController {

    /**
     * Saving the record urgently (either by refreshing or closing the tab), bypasses `onWillSaveRecord`.
     * We disable it to not have the rounding factor saved, as it could potentially brick the DB.
     */
    get modelParams() {
        return { ...super.modelParams, useSendBeaconToSaveUrgently: false };
    }

    async onWillSaveRecord(record) {
        if (record.data.display_rounding_warning &&
            record._values.rounding !== undefined &&
            record.data.rounding < record._values.rounding
        ) {
            if (record.model._urgentSave) {
                // The page is being closed: the confirmation can't be answered, so the change is
                // discarded and the browser asks the user whether to leave the page.
                return false;
            }

            return new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Confirmation Warning"),
                    body: _t(
                        "You're about to permanently change the decimals for all prices in your database.\n" +
                        "This change cannot be undone without technical support."
                    ),
                    confirmLabel: _t("Confirm"),
                    confirm: () => resolve(true),
                    cancel: () => {
                        record.discard();
                        resolve(false);
                    },
                });
            });
        }

        return true;
    }
}

export const currencyFormView = {
    ...formView,
    Controller: CurrencyFormController,
};

registry.category("views").add("currency_form", currencyFormView);
