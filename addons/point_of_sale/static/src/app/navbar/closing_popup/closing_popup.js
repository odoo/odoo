/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { SaleDetailsButton } from "@point_of_sale/app/navbar/sale_details_button/sale_details_button";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { MoneyDetailsPopup } from "@point_of_sale/app/utils/money_details_popup/money_details_popup";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { parseFloat } from "@web/views/fields/parsers";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";

export class ClosePosPopup extends Component {
    static components = { SaleDetailsButton, Input, Dialog };
    static template = "point_of_sale.ClosePosPopup";
    static props = [
        "orders_details",
        "opening_notes",
        "default_cash_details",
        "other_payment_methods",
        "is_manager",
        "amount_authorized_diff",
        "close",
    ];

    setup() {
        this.pos = usePos();
        this.report = useService("report");
        this.hardwareProxy = useService("hardware_proxy");
        this.customerDisplay = useService("customer_display");
        this.dialog = useService("dialog");
        this.state = useState(this.getInitialState());
        this.confirm = useAsyncLockedMethod(this.confirm);
    }
    getInitialState() {
        const initialState = { notes: "", payments: {} };
        if (this.pos.config.cash_control) {
            initialState.payments[this.props.default_cash_details.id] = {
                counted: "0",
            };
        }
        this.props.other_payment_methods.forEach((pm) => {
            if (pm.type === "bank") {
                initialState.payments[pm.id] = {
                    counted: this.env.utils.formatCurrency(pm.amount, false),
                };
            }
        });
        return initialState;
    }

    async confirm() {
        if (
            !this.pos.config.cash_control ||
            this.env.utils.floatIsZero(this.getMaxDifference())
        ) {
            await this.closeSession();
            return;
        }
        if (this.hasUserAuthority()) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Payments Difference"),
                body: _t(
                    "Do you want to accept payments difference and post a profit/loss journal entry?"
                ),
                confirm: this.closeSession.bind(this),
            });
            return;
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Payments Difference"),
            body: _t(
                "The maximum difference allowed is %s.\nPlease contact your manager to accept the closing difference.",
                this.env.utils.formatCurrency(this.props.amount_authorized_diff)
            ),
        });
    }
    async cancel() {
        if (this.canCancel()) {
            this.props.close();
        }
    }
    canConfirm() {
        return Object.values(this.state.payments)
            .map((v) => v.counted)
            .every(this.env.utils.isValidFloat);
    }
    async openDetailsPopup() {
        const action = _t("Cash control - closing");
        this.hardwareProxy.openCashbox(action);
        this.dialog.add(MoneyDetailsPopup, {
            moneyDetails: this.moneyDetails,
            action: action,
            getPayload: (payload) => {
                const { total, moneyDetailsNotes, moneyDetails } = payload;
                this.state.payments[this.props.default_cash_details.id].counted =
                    this.env.utils.formatCurrency(total, false);
                if (moneyDetailsNotes) {
                    this.state.notes = moneyDetailsNotes;
                }
                this.moneyDetails = moneyDetails;
            },
        });
    }
    async downloadSalesReport() {
        return this.report.doAction("point_of_sale.sale_details_report", [
            this.pos.session.id,
        ]);
    }
    setManualCashInput(amount) {
        if (this.env.utils.isValidFloat(amount) && this.moneyDetails) {
            this.state.notes = "";
            this.moneyDetails = null;
        }
    }
    getDifference(paymentId) {
        const counted = this.state.payments[paymentId].counted;
        if (!this.env.utils.isValidFloat(counted)) {
            return NaN;
        }
        const expectedAmount =
            paymentId === this.props.default_cash_details?.id
                ? this.props.default_cash_details.amount
                : this.props.other_payment_methods.find((pm) => pm.id === paymentId).amount;

        return parseFloat(counted) - expectedAmount;
    }
    getMaxDifference() {
        return Math.max(
            ...Object.keys(this.state.payments).map((id) =>
                Math.abs(this.getDifference(parseInt(id)))
            )
        );
    }
    hasUserAuthority() {
        return (
            this.props.is_manager ||
            this.props.amount_authorized_diff == null ||
            this.getMaxDifference() <= this.props.amount_authorized_diff
        );
    }
    canCancel() {
        return true;
    }
    async closeSession() {
        this.customerDisplay?.update({ closeUI: true });
        if (this.pos.config.cash_control) {
            const response = await this.pos.data.call(
                "pos.session",
                "post_closing_cash_details",
                [this.pos.session.id],
                {
                    counted_cash: parseFloat(
                        this.state.payments[this.props.default_cash_details.id].counted
                    ),
                }
            );

            if (!response.successful) {
                return this.handleClosingError(response);
            }
        }

        try {
            await this.pos.data.call("pos.session", "update_closing_control_state_session", [
                this.pos.session.id,
                this.state.notes,
            ]);
        } catch (error) {
            // We have to handle the error manually otherwise the validation check stops the script.
            // In case of "rescue session", we want to display the next popup with "handleClosingError".
            // FIXME
            if (!error.data && error.data.message !== "This session is already closed.") {
                throw error;
            }
        }

        try {
            const bankPaymentMethodDiffPairs = this.props.other_payment_methods
                .filter((pm) => pm.type == "bank")
                .map((pm) => [pm.id, this.getDifference(pm.id)]);
            const response = await this.pos.data.call("pos.session", "close_session_from_ui", [
                this.pos.session.id,
                bankPaymentMethodDiffPairs,
            ]);
            if (!response.successful) {
                return this.handleClosingError(response);
            }
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                // Cannot redirect to backend when offline, let error handlers show the offline popup
                // FIXME POSREF: doing this means closing again when online will redo the beginning of the method
                // although it's impossible to close again because this.closeSessionClicked isn't reset to false
                // The application state is corrupted.
                throw error;
            } else {
                // FIXME POSREF: why are we catching errors here but not anywhere else in this method?
                this.dialog.add(AlertDialog, {
                    title: _t("Closing session error"),
                    body: _t(
                        "An error has occurred when trying to close the session.\n" +
                            "You will be redirected to the back-end to manually close the session."
                    ),
                });
                window.location = "/web#action=point_of_sale.action_client_pos_menu";
            }
        }
    }
    async handleClosingError(response) {
        this.dialog.add(AlertDialog, {
            title: response.title || "Error",
            body: response.message,
        });
        if (response.redirect) {
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        }
    }
}
