import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

const FBR_STATES = {
    to_send: _t("To Send"),
    successful: _t("Successful"),
    unsuccessful: _t("Unsuccessful"),
    successful_demo: _t("Successful (Demo)"),
};

patch(PosOrder.prototype, {
    getFbrStatusLabel() {
        // The related config flag travels with each order, so orders from another
        // company or from a config without FBR enabled stay blank.
        if (!this.l10n_pk_edi_pos_enabled) {
            return "";
        }
        return FBR_STATES[this.l10n_pk_edi_pos_state] || "";
    },

    getOrderlines() {
        const lines = super.getOrderlines(...arguments);
        const saleLines = [];
        const feeLines = [];
        for (const line of lines) {
            (line.isFbrServiceFeeLine() ? feeLines : saleLines).push(line);
        }
        if (!feeLines.length) {
            return lines;
        }
        return [...saleLines, ...feeLines];
    },

    recomputeServiceFees() {
        super.recomputeServiceFees(...arguments);
        this.recomputeFbrServiceFee();
    },

    removeOrderline() {
        const removed = super.removeOrderline(...arguments);
        this.recomputeFbrServiceFee();
        return removed;
    },

    recomputeFbrServiceFee() {
        if (this.state !== "draft") {
            return;
        }
        const feeProduct = this.config.l10n_pk_edi_pos_service_fee_product_id;
        const feeLines = this.lines.filter((line) => line.isFbrServiceFeeLine());
        const isCharged =
            this.config.l10n_pk_edi_pos_charge_service_fee &&
            !this.isRefund &&
            feeProduct &&
            this.lines.some((line) => line.isServiceFeeApplicable());
        if (!isCharged) {
            feeLines.forEach((line) => line.delete());
            return;
        }
        if (feeLines.length) {
            feeLines.slice(1).forEach((line) => line.delete());
            return;
        }
        this.models["pos.order.line"].create({
            order_id: this,
            product_id: feeProduct,
            product_tmpl_id: feeProduct.product_tmpl_id,
            qty: 1,
            price_unit: feeProduct.product_tmpl_id.list_price,
            price_type: "manual",
            tax_ids: [["clear"]],
        });
    },
});
