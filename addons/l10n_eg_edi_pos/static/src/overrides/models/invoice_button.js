import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    click() {
        if (
            this.pos.config.l10n_eg_edi_pos_enable &&
            !["sent", "sent_test"].includes(this.props.order?.l10n_eg_edi_pos_state)
        ) {
            this.dialog.add(WarningDialog, {
                title: _t("ETA Validation Error"),
                message: _t(
                    "Please synchronize this order with ETA first by clicking on Details > Resend to ETA"
                ),
            });
            return;
        }
        return super.click();
    },
});
