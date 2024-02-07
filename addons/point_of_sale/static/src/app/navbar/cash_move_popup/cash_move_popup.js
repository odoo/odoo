/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { parseFloat } from "@web/views/fields/parsers";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

import { CashMoveReceipt } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_receipt/cash_move_receipt";
import { Dialog } from "@web/core/dialog/dialog";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";

export class CashMovePopup extends Component {
    static template = "point_of_sale.CashMovePopup";
    static components = { Input, Dialog };
    static props = ["confirmKey?", "close"];
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.hardwareProxy = useService("hardware_proxy");
        this.printer = useService("printer");
        this.state = useState({
            /** @type {'in'|'out'} */
            type: "out",
            amount: "",
            reason: "",
        });
        this.confirm = useAsyncLockedMethod(this.confirm);
    }

    async confirm() {
        const amount = parseFloat(this.state.amount);
        const formattedAmount = this.env.utils.formatCurrency(amount);
        if (!amount) {
            this.notification.add(_t("Cash in/out of %s is ignored.", formattedAmount));
            return this.props.close();
        }

        const type = this.state.type;
        const translatedType = _t(type);
        const extras = { formattedAmount, translatedType };
        const reason = this.state.reason.trim();
        await this.pos.data.call("pos.session", "try_cash_in_out", [
            [this.pos.session.id],
            type,
            amount,
            reason,
            extras,
        ]);
        await this.pos.logEmployeeMessage(
            `${_t("Cash")} ${translatedType} - ${_t("Amount")}: ${formattedAmount}`,
            "CASH_DRAWER_ACTION"
        );
        await this.printer.print(CashMoveReceipt, {
            reason,
            translatedType,
            formattedAmount,
            headerData: this.pos.getReceiptHeaderData(),
            date: new Date().toLocaleString(),
        });
        this.props.close();
        this.notification.add(
            _t("Successfully made a cash %s of %s.", type, formattedAmount),
            3000
        );
    }
    _onWindowKeyup(event) {
        if (event.key === this.props.confirmKey && !["TEXTAREA"].includes(event.target.tagName)) {
            this.confirm();
        } else {
            super._onWindowKeyup(...arguments);
        }
    }
    onClickButton(type) {
        this.state.type = type;
        this.inputRef.el.focus();
    }
    format(value) {
        return this.env.utils.isValidFloat(value)
            ? this.env.utils.formatCurrency(parseFloat(value))
            : "";
    }
}
