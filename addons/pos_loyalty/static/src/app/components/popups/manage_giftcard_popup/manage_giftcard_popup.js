import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { serializeDate } from "@web/core/l10n/dates";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class ManageGiftCardPopup extends Component {
    static template = "pos_loyalty.ManageGiftCardPopup";
    static components = { Dialog, DateTimeInput };
    static props = {
        title: String,
        placeholder: { type: String, optional: true },
        rows: { type: Number, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        startingValue: "",
        placeholder: "",
        rows: 1,
    };

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.state = useState({
            inputValue: this.props.startingValue,
            amountValue: "",
            error: false,
            amountError: false,
            expirationDate: luxon.DateTime.now().plus({ year: 1 }),
            existingGiftCardId: false,
        });
        this.inputRef = useRef("input");
        this.amountInputRef = useRef("amountInput");
        onMounted(this.onMounted);
    }

    async handleCodeInputEvents(event) {
        clearTimeout(this.timeout);
        this.timeout = setTimeout(async () => {
            if (!this.inputRef.el) {
                this.state.existingGiftCardId = false;
                return;
            }
            this.state.existingGiftCardId = false;
            const [loyaltyCard] = await this.pos.getGiftCard(this.inputRef.el.value.trim());
            if (!loyaltyCard) {
                return;
            }
            const linkedOrderIds = await this.pos.data.call(
                "loyalty.card",
                "get_loyalty_card_linked_orders",
                [loyaltyCard.id]
            );
            if (linkedOrderIds.length) {
                this.state.existingGiftCardId = loyaltyCard.id;
                return this.pos.notification.add(_t("This Gift Card has already been sold."), {
                    type: "danger",
                });
            }
            Object.assign(this.state, {
                amountValue: loyaltyCard.points?.toString(),
                expirationDate: loyaltyCard.expiration_date || false,
            });
            this.state.existingGiftCardId = loyaltyCard.id;
        }, 500);
    }

    onMounted() {
        // Removing the main "DateTimeInput" component's class "o_input" and
        // adding the CSS classes "form-control" and "form-control-lg" for styling the form input with Bootstrap.
        const expirationDateInput = document.querySelector(".o_exp_date_container").children[1];
        expirationDateInput.classList.remove("o_input");
        expirationDateInput.classList.add("form-control", "form-control-lg");
        this.inputRef.el.focus();
    }

    addBalance() {
        if (!this.validateCode()) {
            return;
        }
        this.props.getPayload(
            this.state.inputValue,
            parseFloat(this.state.amountValue),
            this.state.expirationDate ? serializeDate(this.state.expirationDate) : false,
            this.state.existingGiftCardId
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
