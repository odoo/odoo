import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { ReprintReasonPopup } from "@l10n_pt_pos/app/reprint_reason_popup/reprint_reason_popup";

patch(PosStore.prototype, {
    isPortugueseCompany() {
        return this.company.account_fiscal_country_id?.code === "PT";
    },

    /**
     * Tell the cashier why the receipt of ``order`` cannot be printed or sent: its fiscal document
     * (an FS or FR) is only numbered and signed by the server, when the order is synchronised.
     */
    l10nPtExplainDocumentNotIssued(order) {
        const body = !order.isSynced
            ? _t(
                  "The invoice of this order is issued when the order is synchronised with the server, which has not happened yet. Print or send the receipt from the order list once the till is back online. If the till stays offline, issue a pre-printed document to the customer instead, to be recovered in the system later."
              )
            : _t(
                  "The invoice of this order is not signed yet, so its receipt cannot be printed or sent. Try again in a moment; if it still fails, ask a manager to check the order's invoice in the back office."
              );
        this.dialog.add(AlertDialog, { title: _t("Document not issued yet"), body });
    },

    async l10nPtPrepareOrderForReceipt(order, { explainNotIssued = false } = {}) {
        if (!this.isPortugueseCompany()) {
            return true;
        }
        if (!order.isSynced) {
            if (explainNotIssued) {
                this.l10nPtExplainDocumentNotIssued(order);
            }
            return false;
        }

        let orderValues;
        try {
            orderValues = await this.data.call("pos.order", "l10n_pt_get_order_vals", [order.id]);
        } catch (error) {
            this.notification.add(error?.data?.message || _t("Unable to load the receipt data."), {
                type: "warning",
            });
            return false;
        }

        if (!orderValues || !orderValues.hash_short) {
            if (explainNotIssued) {
                this.l10nPtExplainDocumentNotIssued(order);
            }
            return false;
        }

        order.l10nPtIsReprint = orderValues.is_reprint;
        order.l10nPtPosAtcud = orderValues.atcud;
        order.l10nPtPosIdentifier = orderValues.document_identifier;
        order.l10nPtDocumentType = orderValues.document_type;
        order.l10nPtReversedDocument = orderValues.reversed_document;
        order.l10nPtPosInalterableHashShort = orderValues.hash_short;
        order.l10nPtPosQrCodeImage = orderValues.qr_code_image;
        order.l10nPtTrainingMode = orderValues.training_mode;
        return true;
    },

    async printReceipt({ order = this.getOrder(), printBillActionTriggered = false } = {}) {
        // The bill of an order not paid yet is no fiscal document: it prints as such, and is no print
        // of the invoice the order will have.
        if (!this.isPortugueseCompany() || printBillActionTriggered) {
            return super.printReceipt(...arguments);
        }
        const prepared = await this.l10nPtPrepareOrderForReceipt(order, { explainNotIssued: true });
        if (!prepared) {
            return {};
        }

        if (order.l10nPtIsReprint) {
            // A 2ª Via is printed only with the reason for reprinting it.
            const payload = await makeAwaitable(this.dialog, ReprintReasonPopup, {});
            if (!payload) {
                return false;
            }
            await this.data.call("pos.order", "l10n_pt_post_reprint_reason", [
                order.id,
                payload.reprint_reason,
            ]);
        }

        const result = await super.printReceipt(...arguments);
        // Only a print that went through is the document's Original.
        if (result && !order.l10nPtIsReprint) {
            await this.data.call("pos.order", "l10n_pt_update_print_version", [order.id]);
        }
        return result;
    },
});
