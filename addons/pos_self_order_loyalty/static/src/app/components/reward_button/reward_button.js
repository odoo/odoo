import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { UserInputPopup } from "@pos_self_order_loyalty/app/components/popup/user_input_popup/user_input_popup";
import { SelectRewardPopup } from "@pos_self_order_loyalty/app/components/popup/select_reward_popup/select_reward_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

export class RewardButton extends Component {
    static template = "pos_self_order_loyalty.RewardButton";

    setup() {
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.selfOrder = useSelfOrder();
    }

    async clickRewardButton() {
        if (this.selfOrder.currentOrder.getPartner() == null) {
            // Open identification popup
            const mail = await makeAwaitable(this.dialog, UserInputPopup, {
                text: _t(
                    "Scan your customer barcode or fill in your mail address to identify yourself"
                ),
                useMobileScanner: true,
                inputPlaceholder: _t("Enter your email address"),
            });
            if (!mail) {
                return;
            }
            const existingMail = await this.selfOrder.identifyCustomer(mail);
            if (existingMail) {
                const askValidationCode = async () => {
                    const code = await makeAwaitable(this.dialog, UserInputPopup, {
                        text: _t(
                            "A verification code has been sent to %s. It's valid for 10 minutes. If you can't find it, check your spam folder.",
                            existingMail
                        ),
                    });
                    return code;
                };
                let result = false;
                while (!result) {
                    const code = await askValidationCode();
                    if (!code) {
                        return;
                    }
                    result = await this.selfOrder.validateCustomerCode(code, existingMail);
                }
            }
            return;
        }
        // Open reward popup
        this.dialog.add(SelectRewardPopup, {
            getPayload: (reward) => {
                this.selfOrder.applyReward(reward);
            },
            rewardType: "product",
        });
    }

    getPartnerLoyaltyPoints() {
        const cards = this.selfOrder.getLoyaltyCards();
        if (cards.length > 0) {
            return cards[0].program_id.getDisplayPoints(this.selfOrder.currentOrder);
        }
        return false;
    }

    get availableRewardsLength() {
        const programRewards = this.selfOrder.getLoyaltyPrograms("product", false);
        const promotions = this.selfOrder.getPromotionPrograms(false);
        return Object.keys(programRewards).length + Object.keys(promotions).length;
    }
}
