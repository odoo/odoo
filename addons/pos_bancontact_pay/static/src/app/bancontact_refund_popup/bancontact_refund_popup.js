import { Component, computed, signal, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class BancontactRefundPopup extends Component {
    static template = "pos_bancontact_pay.BancontactRefundPopup";
    static components = { Dialog };
    props = useProps({
        lines: t.array(),
        amounts: t.object().optional({}),
        getPayload: t.function(),
        close: t.function(),
    });

    setup() {
        this.pos = usePos();
        this.rows = this.props.lines.map((line) => {
            const amount = signal(this.props.amounts[line.id] ?? "");
            const refundAmount = computed(() => Number(amount()) || 0);
            return {
                line,
                amount,
                refundAmount,
                isInvalid: computed(
                    () =>
                        this.pos.currency.isNegative(refundAmount()) ||
                        this.pos.currency.isPositive(refundAmount() - line.amount_left)
                ),
            };
        });
        this.totalAmount = this.props.lines.reduce((total, line) => total + line.amount, 0);
        this.totalAmountLeft = this.props.lines.reduce(
            (total, line) => total + line.amount_left,
            0
        );
        this.totalRefund = computed(() =>
            this.rows.reduce((total, row) => total + row.refundAmount(), 0)
        );
        this.canConfirm = computed(() => !this.rows.some((row) => row.isInvalid()));
    }

    setMaxAmount(row) {
        row.amount.set(row.line.amount_left);
    }

    confirm() {
        if (!this.canConfirm()) {
            return;
        }
        this.props.getPayload(
            this.rows.map((row) => ({ payment: row.line.payment, amount: row.refundAmount() }))
        );
        this.props.close();
    }
}
