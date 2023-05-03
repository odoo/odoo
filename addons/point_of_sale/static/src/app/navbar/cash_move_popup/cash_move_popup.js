/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { renderToString } from "@web/core/utils/render";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { parseFloat, InvalidNumberError } from "@web/views/fields/parsers";
import { useState } from "@odoo/owl";

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { parse } from "web.field_utils";
import { useValidateCashInput } from "@point_of_sale/js/custom_hooks";

export class CashMovePopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.CashMovePopup";

    setup() {
        super.setup();
        this.notification = useService("pos_notification");
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.state = useState({
            /** @type {'in'|'out'} */
            type: "out",
            amount: "",
            reason: "",
            errorMessage: "",
            parsedAmount: 0,
        });
        this.amountInput = useAutofocus({ refName: "amountInput" });
        useValidateCashInput('amountInput');
    }
    async confirm() {
        let amount;
        try {
            amount = parseFloat(this.state.amount);
        } catch (err) {
            if (!(err instanceof InvalidNumberError)) {
                throw err;
            }
            this.state.errorMessage = this.env._t("Invalid amount");
            return;
        }
        if (amount < 0) {
            this.state.errorMessage = this.env._t("Insert a positive amount");
            return;
        }
        const formattedAmount = this.env.pos.format_currency(amount);
        if (!amount) {
            this.notification.add(
                sprintf(_t("Cash in/out of %s is ignored."), formattedAmount),
                3000
            );
            return this.props.close();
        }

        const type = this.state.type;
        const translatedType = _t(type);
        const extras = { formattedAmount, translatedType };
        const reason = this.state.reason.trim();
        await this.orm.call("pos.session", "try_cash_in_out", [
            [this.env.pos.pos_session.id],
            type,
            amount,
            reason,
            extras,
        ]);
        if (this.env.proxy.printer) {
            const renderedReceipt = renderToString("point_of_sale.CashMoveReceipt", {
                _receipt: {
                    type,
                    reason,
                    amount,
                    translatedType,
                    formattedAmount,
                    cashier: this.env.pos.get_cashier(),
                    company: this.env.pos.company,
                    date: new Date().toLocaleString(),
                },
            });
            const printResult = await this.env.proxy.printer.print_receipt(renderedReceipt);
            if (!printResult.successful) {
                this.popup.add(ErrorPopup, {
                    title: printResult.message.title,
                    body: printResult.message.body,
                });
            }
        }
        this.props.close();
        this.notification.add(
            sprintf(this.env._t("Successfully made a cash %s of %s."), type, formattedAmount),
            3000
        );
    }
    _onAmountKeypress(event) {
        if (["-", "+"].includes(event.key)) {
            event.preventDefault();
        }
    }
    onClickButton(type) {
        this.state.type = type;
        this.state.errorMessage = "";
        this.amountInput.el.focus();
    }
    handleInputChange() {
        if (this.amountInput.el.classList.contains('invalid-cash-input')) {
            this.amountInput.el.parentElement.classList.add('invalid-cash-input');
            this.amountInput.el.style.border = 'none';
            return;
        }
        this.amountInput.el.parentElement.classList.remove('invalid-cash-input');
        this.state.parsedAmount = parse.float(this.state.amount);
    }
}
