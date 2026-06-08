import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async _downloadInvoice(orderId) {
        if (this.pos.company.country_id?.code === "SA") {
            // PDF was deferred at checkout to avoid blocking on wkhtmltopdf.
            // Generate it now on demand before downloading so the user gets
            // the real signed invoice and not the proforma fallback.
            const orderData = (
                await this.pos.data.read("pos.order", [orderId], [], { load: false })
            )[0];
            const accountMoveId = orderData?.raw?.account_move;
            if (accountMoveId) {
                await this.pos.data.call("account.move", "l10n_sa_pos_ensure_invoice_pdf", [
                    accountMoveId,
                ]);
            }
        }
        return super._downloadInvoice(...arguments);
    },
});
