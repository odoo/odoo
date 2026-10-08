import { patch } from "@web/core/utils/patch";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { UserInputPopup } from "@pos_self_order_loyalty/app/components/popup/user_input_popup/user_input_popup";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency } from "@web/core/currency";

patch(PaymentPage.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },
    canAutoSelectFirstMethod() {
        if (
            this.selfOrder.models["loyalty.program"].some((p) =>
                ["ewallet", "gift_card"].includes(p.program_type)
            )
        ) {
            return false;
        }
        return super.canAutoSelectFirstMethod(...arguments);
    },
    get showGiftCardButton() {
        return this.selfOrder.models["loyalty.program"].some((p) => p.program_type === "gift_card");
    },
    get showEwalletButton() {
        const isEwallet = this.selfOrder.models["loyalty.program"].some(
            (p) => p.program_type === "ewallet"
        );
        const partner = this.selfOrder.currentOrder.getPartner();
        return (
            partner &&
            isEwallet &&
            this.selfOrder.models["loyalty.card"].some(
                (c) => c.program_id.program_type === "ewallet" && c.partner_id.id === partner.id
            )
        );
    },
    async scanCode(code) {
        await this.selfOrder._barcodeCouponCodeAction({ code: code });
        const order = await this.selfOrder.sendDraftOrderToServer();
        if (order && this.selfOrder.currency.isZero(order.priceIncl)) {
            this.selfOrder.confirmationPage(
                "pay",
                this.selfOrder.config.self_ordering_mode,
                order.access_token
            );
        }
    },
    useGiftCard() {
        this.dialog.add(UserInputPopup, {
            text: _t("Scan or fill in gift card code to use it."),
            getPayload: (code) => {
                this.scanCode(code);
            },
            useMobileScanner: true,
        });
    },
    useEwallet() {
        this.dialog.add(UserInputPopup, {
            text: _t("Scan or fill in eWallet code to use it."),
            getPayload: (code) => {
                this.scanCode(code);
            },
            useMobileScanner: true,
        });
    },
    cardTotal(type = "gift_card") {
        return this.selfOrder.currentOrder.lines
            .filter(
                (line) => line.is_reward_line && line.reward_id.program_id.program_type === type
            )
            .reduce((acc, line) => acc + line.displayPrice, 0);
    },
    cardTotalDisplay(type = "gift_card") {
        return formatCurrency(this.cardTotal(type), this.selfOrder.currency);
    },
});
