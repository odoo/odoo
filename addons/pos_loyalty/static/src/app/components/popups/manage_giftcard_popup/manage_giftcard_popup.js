import { Component, onMounted, onWillUnmount, useProps, proxy, signal, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { deserializeDateTime, serializeDate } from "@web/core/l10n/dates";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { debounce } from "@bus/workers/bus_worker_utils";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

export class ManageGiftCardPopup extends Component {
    static template = "pos_loyalty.ManageGiftCardPopup";
    static components = { Dialog, DateTimeInput };
    props = useProps({
        title: t.string(),
        placeholder: t.string().optional(""),
        rows: t.number().optional(1),
        startingValue: t.string().optional(""),
        line: t.instanceOf(PosOrderline),
        getPayload: t.function(),
        close: t.function(),
    });

    inputRef = signal.ref();
    amountInputRef = signal.ref();

    setup() {
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.pos = usePos();
        this.state = proxy({
            lockGiftCardFields: false,
            loading: false,
            inputValue: this.props.startingValue,
            amountValue: this.props.line.prices.total_included.toString(),
            error: false,
            errorMessage: "",
            amountError: false,
            expirationDate: luxon.DateTime.now().plus({ year: 1 }),
        });
        this.batchedGiftcardCodeKeydown = debounce(this.checkGiftCard.bind(this), 500);
        onMounted(this.onMounted);
        onWillUnmount(() => this.batchedGiftcardCodeKeydown.cancel());
    }

    onMounted() {
        // Removing the main "DateTimeInput" component's class "o_input" and
        // adding the CSS classes "form-control" and "form-control-lg" for styling the form input with Bootstrap.
        const expirationDateInput = document.querySelector(".o_exp_date_container").children[1];
        expirationDateInput.classList.remove("o_input");
        expirationDateInput.classList.add("form-control", "form-control-lg");
        this.inputRef()?.focus();
    }

    onKeydownGiftCardCode() {
        this.state.loading = true;
        this.batchedGiftcardCodeKeydown();
    }

    async checkGiftCard() {
        this.state.errorMessage = "";
        this.state.error = false;
        // The duplicate check needs no network, so it runs before the offline early return.
        const code = this.state.inputValue.trim();
        const duplicate = this.pos
            .getOrder()
            .getOrderlines()
            .some(
                (other) => other.id !== this.props.line.id && other.gift_card_vals?.code === code
            );
        if (duplicate) {
            this.state.errorMessage = _t(
                "This code is already used by another gift card in this order. Enter a different code."
            );
            this.state.error = true;
            this.state.loading = false;
            return false;
        }
        if (this.pos.data.network.offline) {
            this.state.lockGiftCardFields = false;
            this.state.loading = false;
            return true;
        }
        try {
            const result = await this.pos.data.call("loyalty.card", "get_card_status", [
                code,
                this.pos.config.id,
            ]);

            if (!result.status) {
                this.state.errorMessage = _t(
                    "No gift card matches this code. Check the code and try again."
                );
                this.state.error = true;
                return false;
            }

            if (result["loyalty.card"].length > 0) {
                const giftCard = result["loyalty.card"][0];
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
            this.pos.notification.add(_t("An error occurred while checking the gift card."), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }

        return true;
    }

    async addBalance(ev) {
        if (this.state.loading) {
            return;
        }
        // Check the code as typed now: a pending debounced check would run on stale input.
        this.batchedGiftcardCodeKeydown.cancel();
        this.state.loading = true;
        const isCodeValid = await this.checkGiftCard();
        if (!isCodeValid || !this.validateCode()) {
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
        if (this.state.error || this.state.amountError) {
            return false;
        }
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
