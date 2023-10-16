/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";
import { parseFloat } from "@web/views/fields/parsers";
import { useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";

export class CashMovePopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.CashMovePopup";
    static components = { Input };
    setup() {
        super.setup();
        this.notification = useService("pos_notification");
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.pos = usePos();
        this.hardwareProxy = useService("hardware_proxy");
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
            this.notification.add(_t("Cash in/out of %s is ignored.", formattedAmount), 3000);
            return this.props.close();
        }

        const type = this.state.type;
        const translatedType = _t(type);
        const extras = { formattedAmount, translatedType };
        const reason = this.state.reason.trim();
        await this.orm.call("pos.session", "try_cash_in_out", [
            [this.pos.pos_session.id],
            type,
            amount,
            reason,
            extras,
        ]);
        await this.pos.logEmployeeMessage(
            `${_t("Cash")} ${translatedType} - ${_t("Amount")}: ${formattedAmount}`,
            "CASH_DRAWER_ACTION"
        );

        if (this.hardwareProxy.printer) {
            const renderedReceipt = renderToElement("point_of_sale.CashMoveReceipt", {
                _receipt: {
                    type,
                    reason,
                    amount,
                    translatedType,
                    formattedAmount,
                    cashier: this.pos.get_cashier(),
                    company: this.pos.company,
                    date: new Date().toLocaleString(),
                },
            });
            const printResult = await this.hardwareProxy.printer.printReceipt(renderedReceipt);
            if (!printResult.successful) {
                this.popup.add(ErrorPopup, {
                    title: printResult.message.title,
                    body: printResult.message.body,
                });
            }
        }
        this.props.close();
        this.notification.add(
            _t("Successfully made a cash %s of %s.", type, formattedAmount),
            3000
        );
    }
    _onAmountKeypress(event) {
        if (["-", "+"].includes(event.key)) {
            event.preventDefault();
        }
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
