/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { SaleDetailsButton } from "../ChromeWidgets/SaleDetailsButton";
import { ConfirmPopup } from "./ConfirmPopup";
import { ErrorPopup } from "./ErrorPopup";
import { MoneyDetailsPopup } from "./MoneyDetailsPopup";
import { AlertPopup } from "./AlertPopup";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

export class ClosePosPopup extends AbstractAwaitablePopup {
    static components = { SaleDetailsButton };
    static template = "ClosePosPopup";

    setup() {
        super.setup();
        this.popup = useService("popup");
        this.pos = useService("pos");
        this.manualInputCashCount = false;
        this.cashControl = this.env.pos.config.cash_control;
        this.closeSessionClicked = false;
        this.moneyDetails = null;
        Object.assign(this, this.props.info);
        this.state = useState({
            displayMoneyDetailsPopup: false,
        });
        Object.assign(this.state, this.props.info.state);
    }
    //@override
    async confirm() {
        if (!this.cashControl || !this.hasDifference()) {
            this.closeSession();
        } else if (this.hasUserAuthority()) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: this.env._t("Payments Difference"),
                body: this.env._t(
                    "Do you want to accept payments difference and post a profit/loss journal entry?"
                ),
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
            total: this.manualInputCashCount
                ? 0
                : this.state.payments[this.defaultCashDetails.id].counted,
        });
        if (confirmed) {
            const { total, moneyDetailsNotes, moneyDetails } = payload;
            this.state.payments[this.defaultCashDetails.id].counted = total;
            this.state.payments[this.defaultCashDetails.id].difference =
                this.env.pos.round_decimals_currency(
                    this.state.payments[[this.defaultCashDetails.id]].counted -
                        this.defaultCashDetails.amount
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
    handleInputChange(paymentId) {
        let expectedAmount;
        if (paymentId === this.defaultCashDetails.id) {
            this.manualInputCashCount = true;
            this.moneyDetails = null;
            this.state.notes = "";
            expectedAmount = this.defaultCashDetails.amount;
        } else {
            expectedAmount = this.otherPaymentMethods.find((pm) => paymentId === pm.id).amount;
        }
        this.state.payments[paymentId].difference = this.env.pos.round_decimals_currency(
            this.state.payments[paymentId].counted - expectedAmount
        );
    }
    hasDifference() {
        return Object.entries(this.state.payments).find((pm) => pm[1].difference != 0);
    }
    hasUserAuthority() {
        const absDifferences = Object.entries(this.state.payments).map((pm) =>
            Math.abs(pm[1].difference)
        );
        return (
            this.isManager ||
            this.amountAuthorizedDiff == null ||
            Math.max(...absDifferences) <= this.amountAuthorizedDiff
        );
    }
    canCancel() {
        return true;
    }
    closePos() {
        this.pos.closePos();
    }
    async closeSession() {
        if (!this.closeSessionClicked) {
            this.closeSessionClicked = true;

            const defaultCashCounted = this.env.pos.config.cashControl
                ? this.state.payments[this.defaultCashDetails.id].counted
                : 0;
            this.pos.closeSession(
                defaultCashCounted,
                this.state.notes,
                this.otherPaymentMethods,
                this.state.payments
            );
        }

        this.closeSessionClicked = false;
    }
    async handleClosingError(response) {
        let popupType = "";
        let title = "";

        if (response.type == "alert") {
            popupType = AlertPopup;
            title = response.title ? response.title : "";
        } else {
            popupType = ErrorPopup;
            title = "Error";
        }

        await this.popup.add(popupType, { title: title, body: response.message });
        if (response.redirect) {
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        }
    }
    _getShowDiff(pm) {
        return pm.type == "bank" && pm.number !== 0;
    }
}
