/** @odoo-module */

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { ReprintReasonPopup } from "../../app/reprint_reason_popup/reprint_reason_popup";

patch(PosStore.prototype, {
    async setup(...args) {
        await super.setup(...args);
        const values = await this.data.call("pos.session", "l10n_pt_pos_get_software_info", [
            this.company.id,
            this.config.id,
        ]);
        this.session.l10nPtCertificationNumber = values.l10n_pt_pos_certification_number;
    },

    isPortugueseCompany() {
        return this.company.country_id?.code === "PT";
    },

    /**
     * Tell the cashier why the receipt of ``order`` cannot be printed or sent: its fiscal document
     * (an FS or FR) is only numbered and signed by the server, when the order is synchronised.
     */
    l10nPtExplainDocumentNotIssued(order) {
        const body =
            typeof order?.id !== "number"
                ? _t(
                      "The invoice of this order is issued when the order is synchronised with the server, which has not happened yet. Print or send the receipt from the order list once the till is back online. If the till stays offline, issue a pre-printed document to the customer instead, to be recovered in the system later."
                  )
                : _t(
                      "The invoice of this order is not signed yet, so its receipt cannot be printed or sent. Try again in a moment; if it still fails, ask a manager to check the order's invoice in the back office."
                  );
        this.dialog.add(AlertDialog, { title: _t("Document not issued yet"), body });
    },

    async l10nPtPrepareOrderForReceipt(
        order = this.getOrder(),
        { notifyOnError = true, explainNotIssued = false } = {}
    ) {
        if (!this.isPortugueseCompany()) {
            return true;
        }
        order.l10nPtCertificationNumber = this.session.l10nPtCertificationNumber;
        if (typeof order?.id !== "number") {
            if (explainNotIssued) {
                this.l10nPtExplainDocumentNotIssued(order);
            }
            return false;
        }

        let orderValues;
        try {
            orderValues = await this.data.call("pos.order", "l10n_pt_get_order_vals", [order.id]);
        } catch (error) {
            if (notifyOnError) {
                this.notification.add(
                    error?.data?.message || _t("Unable to load the receipt data."),
                    {
                        type: "warning",
                    }
                );
            }
            return false;
        }

        if (!orderValues || !orderValues.hash_short) {
            if (explainNotIssued) {
                this.l10nPtExplainDocumentNotIssued(order);
            }
            return false;
        }

        order.name = orderValues.name;
        order.isReprint = orderValues.is_reprint;
        order.l10nPtPosAtcud = orderValues.atcud;
        order.l10nPtPosIdentifier = orderValues.document_identifier;
        order.l10nPtDocumentType = orderValues.document_type;
        order.l10nPtPosInalterableHashShort = orderValues.hash_short;
        order.l10nPtPosQrCodeStr = orderValues.qr_code_str
            ? order.l10nPtPosGetQrCodeData(orderValues.qr_code_str)
            : false;
        order.l10nPtTrainingMode = orderValues.training_mode;
        return true;
    },

    async printReceipt({ order = this.getOrder() } = {}) {
        if (!this.isPortugueseCompany()) {
            return super.printReceipt(...arguments);
        }
        const prepared = await this.l10nPtPrepareOrderForReceipt(order, { explainNotIssued: true });
        if (!prepared) {
            return {};
        }

        if (order.isReprint) {
            const payload = await makeAwaitable(this.dialog, ReprintReasonPopup, { order });
            if (payload) {
                await this.data.call("pos.order", "post_reprint_reason", [
                    order.id,
                    payload.reprint_reason,
                ]);
            }
        } else {
            await this.data.call("pos.order", "update_l10n_pt_print_version", [order.id]);
        }

        // Return super to allow printing even if the QR code could not be created
        return super.printReceipt(...arguments);
    },
});
