import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(OrderPaymentValidation.prototype, {
    async finalizeValidation() {
        const result = await super.finalizeValidation(...arguments);
        if (result !== false && this.order.finalized && this.order.isSynced) {
            await this.printGiftCardReports();
        }
        return result;
    },
    /**
     * Print the PDF report (code/barcode) of the virtual gift cards created for this order.
     * `pos.order.read_pos_data` stamps the report action id on each freshly created card as
     * `_pos_report_print_id`, so we can group the cards by report after the order syncs.
     */
    async printGiftCardReports() {
        const reports = {};
        for (const line of this.order.getOrderlines()) {
            const card = line.card_id;
            const reportId = card?.raw?._pos_report_print_id;
            if (reportId) {
                (reports[reportId] ??= []).push(card.id);
            }
        }
        for (const [reportId, cardIds] of Object.entries(reports)) {
            try {
                await this.pos.env.services.report.doAction(Number(reportId), cardIds);
            } catch {
                // A failed print must not roll back an already-validated order.
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Gift card printing failed"),
                    body: _t("The gift card could not be printed. Reprint it from the order."),
                });
            }
        }
    },
});
