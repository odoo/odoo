/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class CurrencyFormController extends FormController {

    async onWillSaveRecord(record) {
        if (record.data.display_rounding_warning &&
            record._values.rounding !== undefined &&
            record.data.rounding < record._values.rounding
        ) {
            return new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Confirmation Warning"),
                    body: _t(
                        "You're about to permanently change the decimals for all prices in your database.\n" +
                        "This change cannot be undone without technical support."
                    ),
                    confirmLabel: _t("Confirm"),
                    cancelLabel: _t("Cancel"),
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
