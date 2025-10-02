import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { deserializeDateTime, serializeDate } from "@web/core/l10n/dates";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { debounce } from "@bus/workers/bus_worker_utils";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";

export class ManageGiftCardPopup extends Component {
    static template = "pos_loyalty.ManageGiftCardPopup";
    static components = { Dialog, DateTimeInput };
    static props = {
        title: String,
        placeholder: { type: String, optional: true },
        rows: { type: Number, optional: true },
        line: Object,
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        startingValue: "",
        placeholder: "",
        rows: 1,
    };

    setup() {
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.pos = usePos();
        this.state = useState({
            lockGiftCardFields: false,
            loading: false,
            inputValue: this.props.startingValue,
            amountValue: this.props.line.prices.total_included.toString(),
            error: false,
            amountError: false,
            expirationDate: luxon.DateTime.now().plus({ year: 1 }),
        });
        this.inputRef = useRef("input");
        this.amountInputRef = useRef("amountInput");
        this.batchedGiftcardCodeKeydown = debounce(this.checkGiftCard.bind(this), 500);
        onMounted(this.onMounted);
    }

    onMounted() {
        // Removing the main "DateTimeInput" component's class "o_input" and
        // adding the CSS classes "form-control" and "form-control-lg" for styling the form input with Bootstrap.
        const expirationDateInput = document.querySelector(".o_exp_date_container").children[1];
        expirationDateInput.classList.remove("o_input");
        expirationDateInput.classList.add("form-control", "form-control-lg");
        this.inputRef.el.focus();
    }

    onKeydownGiftCardCode() {
        this.state.loading = true;
        this.batchedGiftcardCodeKeydown();
    }

    async checkGiftCard() {
        try {
            const code = this.state.inputValue.trim();
            const result = await this.pos.data.call("loyalty.card", "get_gift_card_status", [
                code,
                this.pos.config.id,
            ]);

            if (!result.status) {
                this.dialog.add(AlertDialog, {
                    title: _t("Invalid Gift Card Code"),
                    body: _t(
                        "This code seems to be invalid, please check the Gift Card code and try again."
                    ),
                });
                this.state.error = true;
                this.state.lastCheck = false;
                this.state.inputValue = "";
                return false;
            }

            if (result.data["loyalty.card"].length > 0) {
                const giftCard = result.data["loyalty.card"][0];
                this.state.amountValue = roundCurrency(
                    giftCard.points?.toString() || "0",
                    this.pos.currency
                ).toString();
                this.state.lockGiftCardFields = true;

                if (giftCard.expiration_date) {
                    this.state.expirationDate = deserializeDateTime(giftCard.expiration_date);
                }
            } else {
                this.state.lockGiftCardFields = false;
            }
        } catch (error) {
            logPosMessage(
                "ManageGiftCardPopup",
                "checkGiftCard",
                "Error fetching gift card data",
                false,
                [error]
            );
            this.pos.notification.add({
                type: "danger",
                body: _t("An error occurred while checking the gift card."),
            });
        } finally {
            this.state.error = false;
            this.state.loading = false;
        }

        return true;
    }

    async addBalance(ev) {
        if (!this.validateCode()) {
            return;
        }
        this.props.getPayload(
            this.state.inputValue,
            parseFloat(this.state.amountValue),
            this.state.expirationDate ? serializeDate(this.state.expirationDate) : false
        );
        this.props.close();
    }

    close() {
        this.props.close();
    }

    validateCode() {
        const { inputValue, amountValue } = this.state;
        if (inputValue.trim() === "") {
            this.state.error = true;
            return false;
        }
        if (amountValue.trim() === "") {
            this.state.amountError = true;
            return false;
        }
        return true;
    }

    onExpDateChange(date) {
        this.state.expirationDate = date;
    }
}
