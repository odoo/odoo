import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { parseFloat } from "@web/views/fields/parsers";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

import { CashMoveReceipt } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_receipt/cash_move_receipt";
import { CashMoveListPopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_list_popup/cash_move_list_popup";
import { Dialog } from "@web/core/dialog/dialog";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";

const { DateTime } = luxon;

export class CashMovePopup extends Component {
    static template = "point_of_sale.CashMovePopup";
    static components = { Input, Dialog };
    static props = ["confirmKey?", "close", "getPayload?"];
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
        this.ui = useService("ui");
    }

    get partnerId() {
        return this.pos.user.partner_id.id;
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

        await this.pos.data.call(
            "pos.session",
            "try_cash_in_out",
            this._prepareTryCashInOutPayload(type, amount, reason, this.partnerId, extras),
            {},
            true
        );
        await this.pos.logEmployeeMessage(
            `${_t("Cash")} ${translatedType} - ${_t("Amount")}: ${formattedAmount}`,
            "CASH_DRAWER_ACTION"
        );
        const order = this.pos.models["pos.order"].create({
            session_id: this.pos.session,
            company_id: this.pos.company,
            config_id: this.pos.config,
            user_id: this.pos.user,
            ticket_code: "",
            tracking_number: "",
            sequence_number: 0,
            pos_reference: "",
        });
        await this.printer.print(CashMoveReceipt, {
            reason,
            translatedType,
            order: order,
            formattedAmount,
            date: new Date().toLocaleString(),
        });
        this.pos.models["pos.order"].delete(order);

        this.props.close();
        this.notification.add(
            _t("Successfully made a cash %s of %s.", type, formattedAmount),
            3000
        );
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
    _prepareTryCashInOutPayload(type, amount, reason, partnerId, extras) {
        return [[this.pos.session.id], type, amount, reason, partnerId, extras];
    }
    isValidCashMove() {
        return this.env.utils.isValidFloat(this.state.amount) && this.state.reason.trim() !== "";
    }
    async openDetails() {
        const cashMoves = await this.pos.data.call("pos.session", "get_cash_in_out_list", [
            this.pos.session.id,
        ]);
        this.dialog.add(CashMoveListPopup, {
            cashMoves: cashMoves.map((m) => ({
                ...m,
                date: DateTime.fromSQL(m.date, { zone: "UTC" }).setZone("local"),
            })),
            partnerId: this.partnerId,
        });
    }
    async openNumpadDialog() {
        if (!this.ui.isSmall) {
            return;
        }

        const result = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Amount"),
            startingValue: this.state.amount,
        });

        if (result) {
            this.state.amount = result;
        }
    }
}
