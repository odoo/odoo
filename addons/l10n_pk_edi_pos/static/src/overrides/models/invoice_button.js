import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    click() {
        if (
            this.pos.config.l10n_pk_edi_pos_enabled &&
            !["successful", "successful_demo"].includes(this.props.order.l10n_pk_edi_pos_state)
        ) {
            this.dialog.add(WarningDialog, {
                title: _t("Odoo Warning"),
                message: _t(
                    "Please submit this order to the FBR first. Only successful orders can be invoiced."
                ),
            });
            return;
        }
        return super.click();
    },
});
