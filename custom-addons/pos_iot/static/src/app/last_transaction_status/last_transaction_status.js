/** @odoo-module */
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { useService } from "@web/core/utils/hooks";
import { useState, Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";

/**
 * Last Transaction Status Button
 *
 * Retrieve the status of the last transaction processed by the connected
 * Worldline payment terminal and opens a popup to display the result.
 */
export class LastTransactionStatusButton extends Component {
    static template = "pos_iot.LastTransactionStatusButton";

    setup() {
        this.popup = useService("popup");
        this.state = useState({ pending: false });
        this.pos = usePos();

        // Precompute the worldline payment methods values

        // An IoT box can only support one WorldLine payment terminal
        // However, several payment method can use the same terminal (eco/meal vouchers for instance)
        // In some cases, there is no need to perform several call to the same IoT and might cause errors
        this.worldline_payment_method_terminals = [];
        const worldlineTerminalIoT = new Set();

        this.pos.payment_methods.filter(pm => pm.use_payment_terminal === 'worldline').forEach(worldline_pm => {
            const terminal = worldline_pm.payment_terminal && worldline_pm.payment_terminal.get_terminal();
            const terminalIoTIP = terminal && terminal.iotIp;
            if (terminal && terminalIoTIP && !worldlineTerminalIoT.has(terminalIoTIP)) {
                this.worldline_payment_method_terminals.push(terminal);
                worldlineTerminalIoT.add(terminalIoTIP);
            }
        });
    }

    sendLastTransactionStatus() {
        if (this.state.pending) {
            return;
        }

        const status = this.pos.get_order()?.selected_paymentline?.payment_status;
        if (status && ["waiting", "waitingCard", "waitingCancel"].includes(status)) {
            this.popup.add(ErrorPopup, {
                title: _t("Electronic payment in progress"),
                body: _t(
                    "You cannot check the status of the last transaction when a payment in in progress."
                ),
            });
            return;
        }
        this.state.pending = true;
        if (this.worldline_payment_method_terminals.length === 0) {
            this.state.pending = false;
            this.popup.add(ErrorPopup, {
                'title': _t('No worldline terminal configured'),
                'body': _t('No worldline terminal device configured for any payment methods. ' +
                    'Double check if your configured payment method define the field Payment Terminal Device')
            });
        }
        else {
            this.worldline_payment_method_terminals.forEach(worldline_terminal => {
                worldline_terminal.addListener(this._onLastTransactionStatus.bind(this));
                worldline_terminal.action({ messageType: "LastTransactionStatus" }).catch(() => {
                    this.state.pending = false;
                });
            });
        }
    }

    _onLastTransactionStatus(data) {
        // If the response data has a cid,
        // it's not a response to a Last Transaction Status request
        if (data.cid)
            return;

        this.state.pending = false;
        this.popup.add(LastTransactionPopup, data.value);
    }
}

/**
 * Last Transaction Popup
 *
 * Displays the result of the last transaction processed by the connected
 * Worldline payment terminal
 */
export class LastTransactionPopup extends AbstractAwaitablePopup {
    static template = "pos_iot.LastTransactionPopup";
    static defaultProps = { cancelKey: false };
}
