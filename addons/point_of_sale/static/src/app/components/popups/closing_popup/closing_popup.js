import { Dialog } from "@web/core/dialog/dialog";
import { SaleDetailsButton } from "@point_of_sale/app/components/navbar/sale_details_button/sale_details_button";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { MoneyDetailsPopup } from "@point_of_sale/app/components/popups/money_details_popup/money_details_popup";
import { useService } from "@web/core/utils/hooks";
import { Component, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { parseFloat } from "@web/views/fields/parsers";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
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
    get cashMoveData() {
        const { total, moves } = this.props.default_cash_details.moves.reduce(
            (acc, move, i) => {
                acc.total += move.amount;
                acc.moves.push({
                    id: i,
                    name: move.name,
                    amount: move.amount,
                });
                return acc;
            },
            { total: 0, moves: [] }
        );
        return { total, moves };
    }
    get orderForNextDays() {
        const today = DateTime.now();
        return this.pos.models["pos.order"].filter(
            (o) => o.lines.length > 0 && o.preset_time > today && o.state === "draft"
        ).length;
    }
    async cashMove() {
        await this.pos.cashMove();
        this.dialog.closeAll();
        this.pos.closeSession();
    }
    getInitialState() {
        const initialState = { notes: "", payments: {} };
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
                    this.state.notes = moneyDetailsNotes;
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
            this.state.notes = "";
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

        try {
            const context = {
                device_identifier: this.pos.device.identifier,
            };
            const amountByPaymentMethod = Object.entries(this.state.payments).reduce(
                (acc, [id, { counted }]) => {
                    acc[id] = parseFloat(counted);
                    return acc;
                },
                {}
            );
            const response = await this.pos.data.call(
                "pos.session",
                "close_session_from_ui",
                [this.pos.session.id, amountByPaymentMethod],
                { context }
            );
            if (!response.status) {
                return this.handleClosingError(response);
            }

            this.pos.session.state = "closed";
            try {
                await this.pos.ticketPrinter.printSaleDetailsReceipt({ download: true });
            } finally {
                this.pos.router.close();
            }
        } finally {
            localStorage.removeItem(`pos.session.${odoo.pos_config_id}`);
        }
    }
    async handleClosingError(response) {
        if (response.type === "session_already_closed") {
            return await makeAwaitable(
                this.dialog,
                AlertDialog,
                {
                    title: _t("Session Already Closed"),
                    body: response.message,
                },
                {
                    onClose: () => {
                        window.location.reload();
                    },
                }
            );
        } else if (response.type === "draft_orders") {
            return await makeAwaitable(this.dialog, ConfirmationDialog, {
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
        }
    }
    getMovesTotalAmount() {
        const amounts = this.props.default_cash_details.moves.map((move) => move.amount);
        return amounts.reduce((acc, x) => acc + x, 0);
    }
    get validPms() {
        return this.props.non_cash_payment_methods.filter(
            (pm) => pm.number !== 0 && (pm.type === "bank" || pm.type === "cash")
        );
    }
    isTheLastPM(pm) {
        return pm === this.validPms.at(-1) && this.validPms.length % 2 === 0;
    }

    isOnePmUsed() {
        return this.validPms.length == 0;
    }
}
