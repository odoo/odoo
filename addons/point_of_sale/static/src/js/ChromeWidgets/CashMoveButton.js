/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";
import { _t } from "web.core";
import { renderToString } from "@web/core/utils/render";

const TRANSLATED_CASH_MOVE_TYPE = {
    in: _t("in"),
    out: _t("out"),
};

class CashMoveButton extends PosComponent {
    async onClick() {
        const { confirmed, payload } = await this.showPopup("CashMovePopup");
        if (!confirmed) {
            return;
        }
        const { type, amount, reason } = payload;
        const translatedType = TRANSLATED_CASH_MOVE_TYPE[type];
        const formattedAmount = this.env.pos.format_currency(amount);
        if (!amount) {
            return this.showNotification(
                _.str.sprintf(this.env._t("Cash in/out of %s is ignored."), formattedAmount),
                3000
            );
        }
        const extras = { formattedAmount, translatedType };
        await this.rpc({
            model: "pos.session",
            method: "try_cash_in_out",
            args: [[this.env.pos.pos_session.id], type, amount, reason, extras],
        });
        if (this.env.proxy.printer) {
            const renderedReceipt = renderToString("point_of_sale.CashMoveReceipt", {
                _receipt: this._getReceiptInfo({ ...payload, translatedType, formattedAmount }),
            });
            const printResult = await this.env.proxy.printer.print_receipt(renderedReceipt);
            if (!printResult.successful) {
                this.showPopup("ErrorPopup", {
                    title: printResult.message.title,
                    body: printResult.message.body,
                });
            }
        }
        this.showNotification(
            _.str.sprintf(this.env._t("Successfully made a cash %s of %s."), type, formattedAmount),
            3000
        );
    }
    _getReceiptInfo(payload) {
        const result = { ...payload };
        result.cashier = this.env.pos.get_cashier();
        result.company = this.env.pos.company;
        return result;
    }
}
CashMoveButton.template = "point_of_sale.CashMoveButton";

Registries.Component.add(CashMoveButton);

export default CashMoveButton;
