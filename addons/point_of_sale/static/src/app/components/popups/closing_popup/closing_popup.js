import { Dialog } from "@web/core/dialog/dialog";
import { SaleDetailsButton } from "@point_of_sale/app/components/navbar/sale_details_button/sale_details_button";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { MoneyDetailsPopup } from "@point_of_sale/app/components/popups/money_details_popup/money_details_popup";
import { useService } from "@web/core/utils/hooks";
import { Component, proxy } from "@odoo/owl";
import { roundPrecision } from "@web/core/utils/numbers";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { parseFloat } from "@web/views/fields/parsers";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { PaymentMethodBreakdown } from "@point_of_sale/app/components/payment_method_breakdown/payment_method_breakdown";
import { CashInput } from "@point_of_sale/app/components/inputs/input/cash_input/cash_input";

const { DateTime } = luxon;

export class ClosePosPopup extends Component {
    static components = { SaleDetailsButton, Dialog, PaymentMethodBreakdown, CashInput };
    static template = "point_of_sale.ClosePosPopup";
    static props = [
        "orders_details",
        "opening_notes",
        "default_cash_details",
        "non_cash_payment_methods",
        "is_manager",
        "amount_authorized_diff",
        "close",
    ];

    setup() {
        this.pos = usePos();
        this.report = useService("report");
        this.dialog = useService("dialog");
        this.ui = useService("ui");
        this.state = proxy(this.getInitialState());
        this.confirm = useAsyncLockedMethod(this.confirm);
    }
    get orderForNextDays() {
        const today = DateTime.now();
        return this.pos.models["pos.order"].filter(
            (o) => o.lines.length > 0 && o.preset_time > today && o.state === "draft"
        ).length;
    }
    get paymentMethods() {
        const paymentMethods = [...this.props.non_cash_payment_methods].sort(
            (a, b) => a.editable - b.editable // Move editable payment methods to the end
        );
        const cashDetails = this.props.default_cash_details;
        if (!Object.keys(cashDetails).length) {
            return paymentMethods;
        }
        const defaultCashMethod = {
            ...cashDetails,
            isDefaultCash: true,
            editable: true,
        };

        // To ensure the cash payment info are at always on right side of bottom row
        if (paymentMethods.length % 2 === 0 || this.ui.isSmall) {
            paymentMethods.push(defaultCashMethod);
        } else {
            paymentMethods.splice(-1, 0, defaultCashMethod);
        }
        return paymentMethods;
    }
    get cashTransactionSummary() {
        const { statement_amount, payment_amount } = this.props.default_cash_details.cash_breakdown;
        const transactionList = [
            {
                id: 0,
                name: _t("Cash in/out"),
                amount: statement_amount,
            },
            {
                // Payments should be last in the list, and it
                // will be replaced with per employee payments in pos_hr
                id: 1,
                name: _t("Payments"),
                amount: payment_amount,
            },
        ];
        return {
            total: statement_amount + payment_amount,
            list: transactionList,
        };
    }
    async cashMove() {
        await this.pos.cashMove();
        this.dialog.closeAll();
        this.pos.closeSession();
    }
    getInitialState() {
        const initialState = {
            notes: {
                opening_notes: this.props.opening_notes,
                closing_notes: "",
            },
            payments: {},
        };
        if (this.pos.config.cash_control) {
            const defaultCash = this.props.default_cash_details;
            initialState.payments[defaultCash.id] = {
                counted: this.env.utils.formatCurrency(defaultCash.amount, false),
            };
        }
        this.props.non_cash_payment_methods.forEach((pm) => {
            initialState.payments[pm.id] = {
                counted: this.env.utils.formatCurrency(pm.amount || 0, false),
            };
        });
        return initialState;
    }
    async confirm() {
        if (!this.pos.config.cash_control || this.pos.currency.isZero(this.getMaxDifference())) {
            await this.closeSession();
            return;
        }
        if (this.hasUserAuthority()) {
            const response = await ask(this.dialog, {
                title: _t("Payments Difference"),
                body: _t(
                    "The money counted doesn't match what we expected. Want to log the difference for the books?"
                ),
                confirmLabel: _t("Proceed Anyway"),
                cancelLabel: _t("Discard"),
            });
            if (response) {
                return this.closeSession();
            }
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
        this.pos.openCashbox(action);
        this.dialog.add(MoneyDetailsPopup, {
            moneyDetails: this.moneyDetails,
            action: action,
            getPayload: (payload) => {
                const { total, moneyDetailsNotes, moneyDetails } = payload;
                this.state.payments[this.props.default_cash_details.id].counted =
                    this.env.utils.formatCurrency(total, false);
                if (moneyDetailsNotes) {
                    this.state.notes.closing_notes = moneyDetailsNotes;
                }
                this.moneyDetails = moneyDetails;
            },
            context: "Closing",
        });
    }
    async downloadSalesReport() {
        return this.report.doAction("point_of_sale.sale_details_report", [this.pos.session.id]);
    }
    setManualCashInput(amount) {
        if (this.env.utils.isValidFloat(amount) && this.moneyDetails) {
            this.state.notes.closing_notes = "";
            this.moneyDetails = null;
        }
    }
    handleCashCountBlur() {
        const counted = this.state.payments[this.props.default_cash_details.id].counted;
        this.setManualCashInput(counted);
        this.state.payments[this.props.default_cash_details.id].counted =
            this.env.utils.parseAndFormatCurrency(counted);
    }
    handlePaymentCountBlur(paymentId) {
        this.state.payments[paymentId].counted = this.env.utils.parseAndFormatCurrency(
            this.state.payments[paymentId].counted
        );
    }
    getDifference(paymentId) {
        const counted = this.state.payments[paymentId].counted;
        if (!this.env.utils.isValidFloat(counted)) {
            return NaN;
        }
        const expectedAmount =
            paymentId === this.props.default_cash_details?.id
                ? this.props.default_cash_details.amount
                : this.props.non_cash_payment_methods.find((pm) => pm.id === paymentId).amount;

        return roundPrecision(parseFloat(counted) - expectedAmount, this.pos.currency.rounding);
    }

    getMaxDifference() {
        return Math.max(
            ...Object.keys(this.state.payments).map((id) =>
                Math.abs(this.getDifference(parseInt(id)))
            )
        );
    }
    hasUserAuthority() {
        return this.props.is_manager || this.allowedDifference();
    }
    allowedDifference() {
        return (
            this.props.amount_authorized_diff == null ||
            this.getMaxDifference() <= this.props.amount_authorized_diff
        );
    }
    canCancel() {
        return true;
    }
    async closeSession() {
        this.pos._resetConnectedCashier();
        // If there are orders in the db left unsynced, we try to sync.
        const syncSuccess = await this.pos.pushOrdersWithClosingPopup();
        if (!syncSuccess) {
            return;
        }
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
            const bankPaymentMethodDiffPairs = this.props.non_cash_payment_methods
                .filter((pm) => pm.type == "bank")
                .map((pm) => [pm.id, this.getDifference(pm.id)]);
            const response = await this.pos.data.call(
                "pos.session",
                "close_session_from_ui",
                [this.pos.session.id, bankPaymentMethodDiffPairs],
                {
                    context: {
                        device_identifier: this.pos.device.identifier,
                    },
                }
            );
            if (!response.successful) {
                return this.handleClosingError(response);
            }
            this.pos.session.state = "closed";
            try {
                await this.pos.ticketPrinter.printSaleDetailsReceipt({ download: true });
            } finally {
                this.pos.router.close();
            }
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                throw error;
            } else {
                await this.handleClosingControlError();
            }
        } finally {
            localStorage.removeItem(`pos.session.${odoo.pos_config_id}`);
        }
    }
    async handleClosingControlError() {
        this.dialog.add(
            AlertDialog,
            {
                title: _t("Closing session error"),
                body: _t(
                    "An error has occurred when trying to close the session.\n" +
                        "You will be redirected to the back-end to manually close the session."
                ),
            },
            {
                onClose: () => {
                    this.dialog.add(
                        FormViewDialog,
                        {
                            resModel: "pos.session",
                            resId: this.pos.session.id,
                        },
                        {
                            onClose: async () => {
                                const session = await this.pos.data.read("pos.session", [
                                    this.pos.session.id,
                                ]);
                                if (session[0] && session[0].state === "closed") {
                                    this.pos.router.close();
                                } else {
                                    this.pos.redirectToBackend();
                                }
                            },
                        }
                    );
                },
            }
        );
    }
    async handleClosingError(response) {
        this.dialog.add(ConfirmationDialog, {
            title: response.title || "Oh snap !",
            body: response.message,
            confirmLabel: _t("Review Orders"),
            cancelLabel: _t("Cancel Orders"),
            confirm: () => {
                if (!response.redirect) {
                    this.props.close();
                    this.pos.navigate("TicketScreen");
                }
            },
            cancel: async () => {
                if (!response.redirect) {
                    const now = DateTime.now();
                    const ordersDraft = this.pos.models["pos.order"].filter(
                        (o) => !o.finalized && !(o.preset_time && o.preset_time > now)
                    );
                    await this.pos.deleteOrders(ordersDraft, response.open_order_ids);
                    this.closeSession();
                }
            },
            dismiss: async () => {},
        });

        if (response.redirect) {
            this.pos.router.close();
        }
    }
}
