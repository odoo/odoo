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
        });
        this.inputRef = useRef("input");
        this.amountInputRef = useRef("amountInput");
        this.bufferedInput = "";
        this.isBackendGiftCard = false;
        onMounted(this.onMounted);
    }

    async handleCodeInputEvents(event) {
        const isEndCharacter = event.key?.match(/(Enter|Tab)/);
        const isSpecialKey =
            !["Control", "Alt"].includes(event.key) && (event.key?.length > 1 || event.metaKey);

        if (isEndCharacter || event.type === "focusout") {
            const [loyalty_card] = await this.pos.data.searchRead(
                "loyalty.card",
                [
                    "&",
                    ["program_type", "=", "gift_card"],
                    ["code", "=", this.inputRef.el.value.trim()],
                ],
                []
            );
            if (!loyalty_card) {
                return;
            }
            const linked_order_ids = await this.pos.data.call(
                "loyalty.card",
                "get_loyalty_card_order_ids",
                [loyalty_card.id]
            );
            if (linked_order_ids.length) {
                return this.pos.notification.add(_t("This Gift card has already been sold."), {
                    type: "danger",
                });
            }

            Object.assign(this.state, {
                amountValue: loyalty_card.points?.toString(),
                expirationDate: loyalty_card.expiration_date || false,
            });
            this.isBackendGiftCard = true;
        } else if (!isSpecialKey) {
            this.bufferedInput += event.key;
        }
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
            this.isBackendGiftCard
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
