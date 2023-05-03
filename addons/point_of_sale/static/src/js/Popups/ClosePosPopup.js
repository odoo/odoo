/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { SaleDetailsButton } from "../ChromeWidgets/SaleDetailsButton";
import { ConfirmPopup } from "./ConfirmPopup";
import { MoneyDetailsPopup } from "./MoneyDetailsPopup";
import { useService } from "@web/core/utils/hooks";
import { AlertPopup } from "./AlertPopup";
import { ErrorPopup } from "./ErrorPopup";
import { useState } from "@odoo/owl";
import { ConnectionLostError } from "@web/core/network/rpc_service";
import { identifyError } from "@point_of_sale/app/error_handlers/error_handlers";
import { _t } from "@web/core/l10n/translation";
import { parse } from "web.field_utils";
import { useValidateCashInput } from "@point_of_sale/js/custom_hooks";

export class ClosePosPopup extends AbstractAwaitablePopup {
    static components = { SaleDetailsButton };
    static template = "ClosePosPopup";

    setup() {
        super.setup();
        this.popup = useService("popup");
        this.pos = useService("pos");
        this.orm = useService("orm");
        this.manualInputCashCount = false;
        this.cashControl = this.env.pos.config.cash_control;
        this.closeSessionClicked = false;
        this.moneyDetails = null;
        Object.assign(this, this.props.info);
        this.state = useState({
            displayMoneyDetailsPopup: false,
        });
        Object.assign(this.state, this.props.info.state);
        useValidateCashInput("closingCashInput");
        if (this.otherPaymentMethods.length > 0) {
            this.otherPaymentMethods.forEach(pm => {
                if (this._getShowDiff(pm)) {
                    useValidateCashInput("closingCashInput_" + pm.id, this.state.payments[pm.id].counted);
                }
            })
        }
    }
    //@override
    async confirm() {
        if (!this.cashControl || !this.hasDifference()) {
            this.closeSession();
        } else if (this.hasUserAuthority()) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: this.env._t("Payments Difference"),
                body: this.env._t("Do you want to accept payments difference and post a profit/loss journal entry?"),
            });
            if (confirmed) {
                this.closeSession();
            }
        } else {
            await this.popup.add(ConfirmPopup, {
                title: this.env._t("Payments Difference"),
                body: _.str.sprintf(
                    this.env._t(
                        "The maximum difference allowed is %s.\n\
                        Please contact your manager to accept the closing difference."
                    ),
                    this.env.pos.format_currency(this.amountAuthorizedDiff)
                ),
                confirmText: this.env._t("OK"),
            });
        }
    }
    //@override
    async cancel() {
        if (this.canCancel()) {
            super.cancel();
        }
    }
    async openDetailsPopup() {
        const { confirmed, payload } = await this.popup.add(MoneyDetailsPopup, {
            moneyDetails: this.moneyDetails,
            total: this.manualInputCashCount ? 0 : this.state.payments[this.defaultCashDetails.id].counted,
        });
        if (confirmed) {
            const { total, moneyDetailsNotes, moneyDetails } = payload;
            this.state.payments[this.defaultCashDetails.id].counted = total;
            this.state.payments[this.defaultCashDetails.id].difference = this.env.pos.round_decimals_currency(
                this.state.payments[[this.defaultCashDetails.id]].counted - this.defaultCashDetails.amount
            );
            if (moneyDetailsNotes) {
                this.state.notes = moneyDetailsNotes;
            }
            this.manualInputCashCount = false;
            this.moneyDetails = moneyDetails;
        }
    }
    async downloadSalesReport() {
        await this.env.legacyActionManager.do_action("point_of_sale.sale_details_report", {
            additional_context: {
                active_ids: [this.env.pos.pos_session.id],
            },
        });
    }
    handleInputChange(paymentId, event) {
        if (event.target.classList.contains('invalid-cash-input')) return;
        let expectedAmount;
        if (paymentId === this.defaultCashDetails.id) {
            this.manualInputCashCount = true;
            this.moneyDetails = null;
            this.state.notes = "";
            expectedAmount = this.defaultCashDetails.amount;
        } else {
            expectedAmount = this.otherPaymentMethods.find((pm) => paymentId === pm.id).amount;
        }
        this.state.payments[paymentId].counted = parse.float(event.target.value);
        this.state.payments[paymentId].difference = this.env.pos.round_decimals_currency(
            this.state.payments[paymentId].counted - expectedAmount
        );
    }
    hasDifference() {
        return Object.entries(this.state.payments).find((pm) => pm[1].difference != 0);
    }
    hasUserAuthority() {
        const absDifferences = Object.entries(this.state.payments).map((pm) => Math.abs(pm[1].difference));
        return (
            this.isManager ||
            this.amountAuthorizedDiff == null ||
            Math.max(...absDifferences) <= this.amountAuthorizedDiff
        );
    }
    canCancel() {
        return true;
    }
    async closeSession() {
        if (!this.closeSessionClicked) {
            this.closeSessionClicked = true;

            if (this.cashControl) {
                const response = await this.orm.call(
                    "pos.session",
                    "post_closing_cash_details",
                    [this.env.pos.pos_session.id],
                    {
                        counted_cash: this.state.payments[this.defaultCashDetails.id].counted,
                    }
                );

                if (!response.successful) {
                    return this.handleClosingError(response);
                }
            }

            try {
                await this.orm.call("pos.session", "update_closing_control_state_session", [
                    this.env.pos.pos_session.id,
                    this.state.notes,
                ]);
            } catch (error) {
                // We have to handle the error manually otherwise the validation check stops the script.
                // In case of "rescue session", we want to display the next popup with "handleClosingError".
                // FIXME
                if (
                    !error.message &&
                    !error.message.data &&
                    error.message.data.message !== "This session is already closed."
                ) {
                    throw error;
                }
            }

            try {
                const bankPaymentMethodDiffPairs = this.otherPaymentMethods
                    .filter((pm) => pm.type == "bank")
                    .map((pm) => [pm.id, this.state.payments[pm.id].difference]);
                const response = await this.orm.call("pos.session", "close_session_from_ui", [
                    this.env.pos.pos_session.id,
                    bankPaymentMethodDiffPairs,
                ]);
                if (!response.successful) {
                    return this.handleClosingError(response);
                }
                window.location = "/web#action=point_of_sale.action_client_pos_menu";
            } catch (error) {
                if (identifyError(error) instanceof ConnectionLostError) {
                    // Cannot redirect to backend when offline, let error handlers show the offline popup
                    // FIXME POSREF: doing this means closing again when online will redo the beginning of the method
                    // although it's impossible to close again because this.closeSessionClicked isn't reset to false
                    // The application state is corrupted.
                    throw error;
                } else {
                    // FIXME POSREF: why are we catching errors here but not anywhere else in this method?
                    await this.popup.add(ErrorPopup, {
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

        this.closeSessionClicked = false;
    }
    async handleClosingError(response) {
        const body = response.message;
        if (response.type == "alert") {
            await this.popup.add(AlertPopup, { title: response.title || "", body });
        } else {
            await this.popup.add(ErrorPopup, { title: "Error", body });
        }

        if (response.redirect) {
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        }
    }
    _getShowDiff(pm) {
        return pm.type == "bank" && pm.number !== 0;
    }
}
