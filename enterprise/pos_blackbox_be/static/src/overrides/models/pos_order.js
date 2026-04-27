/* global Sha1 */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    doNotAllowRefundAndSales() {
        return this.useBlackBoxBe() || super.doNotAllowRefundAndSales();
    },
    useBlackBoxBe() {
        return Boolean(this.config.iface_fiscal_data_module);
    },
    checkIfUserClocked() {
        const cashierId = this.user.id;
        if (this.config.module_pos_hr) {
            return this.session.employees_clocked_ids.find((elem) => elem.id === cashierId);
        }
        return this.session.users_clocked_ids.find((elem) => elem.id === cashierId);
    },
    getTaxAmountByPercent(tax_percentage, lines = false) {
        if (!lines) {
            lines = this.get_orderlines();
        }
        const tax = this.get_tax_details_of_lines(lines).find(
            (tax) => tax.tax_percentage === tax_percentage
        );
        return tax ? tax.amount : false;
    },
    wait_for_push_order() {
        const result = super.wait_for_push_order();
        return Boolean(this.useBlackBoxBe() || result);
    },
    getPlu(lines = null) {
        if (lines === null) {
            lines = this.lines;
        }
        let order_str = "";
        lines.forEach((line) => (order_str += line.generatePluLine()));
        const sha1 = Sha1.hash(order_str);
        return sha1.slice(sha1.length - 8);
    },
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        result.useBlackboxBe = Boolean(this.useBlackBoxBe());
        if (this.useBlackBoxBe()) {
            result.blackboxBeData = {
                original_order: this.originalSplittedOrder?.pos_reference,
                pluHash: this.plu_hash,
                receipt_type: this.uiState.receipt_type,
                terminalId: this.config.id,
                blackboxDate: this.blackbox_date,
                blackboxTime: this.blackbox_time,

                blackboxSignature: this.blackbox_signature,
                versionId: this.session._server_version.server_version,

                vscIdentificationNumber: this.blackbox_vsc_identification_number,
                blackboxFdmNumber: this.blackbox_unique_fdm_production_number,
                blackbox_ticket_counter: this.blackbox_ticket_counter,
                blackbox_total_ticket_counter: this.blackbox_total_ticket_counter,
                ticketCounter: this.blackbox_ticket_counters,
                fdmIdentifier: this.config.certified_blackbox_identifier,
            };
        }
        return result;
    },
    isValidNegativeOrder() {
        return (
            !this._isRefundOrder() &&
            this.lines.length > 0 &&
            this.lines.every((line) => line.get_quantity() <= 0)
        );
    },
});
