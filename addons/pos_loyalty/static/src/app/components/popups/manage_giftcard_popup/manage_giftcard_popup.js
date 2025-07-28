import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { deserializeDateTime, serializeDate } from "@web/core/l10n/dates";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

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
            loading: false,
            inputValue: this.props.startingValue,
            amountValue: this.props.line.getPriceWithTax().toString(),
            error: false,
            amountError: false,
            expirationDate: luxon.DateTime.now().plus({ year: 1 }),
        });
        this.inputRef = useRef("input");
        this.amountInputRef = useRef("amountInput");
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

    async checkGiftCard() {
        const code = this.state.inputValue.trim();
        if (code === "") {
            this.state.error = true;
            this.state.lastCheck = false;
            this.props.close();
            return false;
        }

        this.state.loading = true;
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
            this.props.close();
            return false;
        }

        if (result.data["loyalty.card"].length > 0) {
            const giftCard = result.data["loyalty.card"][0];
            this.state.amountValue = giftCard.points.toFixed(2);

            if (giftCard.expiration_date) {
                this.state.expirationDate = deserializeDateTime(giftCard.expiration_date);
            }

            this.pos.notification.add(
                _t(
                    "A gift card has already been generated with this code. It has been added to the order. Please check the amount. (%s)",
                    giftCard.code
                ),
                {
                    type: "warning",
                }
            );
        }

        this.state.error = false;
        return true;
    }

    async addBalance(ev) {
        const check = await this.checkGiftCard();
        if (!check) {
            this.props.close();
            return;
        }

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
