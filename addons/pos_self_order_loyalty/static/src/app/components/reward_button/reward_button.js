import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { BarcodeScannerPopup } from "@pos_self_order_loyalty/app/components/popup/barcode_scanner_popup/barcode_scanner_popup";
import { SelectRewardPopup } from "@pos_self_order_loyalty/app/components/popup/select_reward_popup/select_reward_popup";

export class RewardButton extends Component {
    static template = "pos_self_order_loyalty.RewardButton";
    static props = {};

    setup() {
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.selfOrder = useSelfOrder();
    }

    clickRewardButton() {
        if (this.selfOrder.currentOrder.getPartner() == null) {
            // Open identification popup
            this.dialog.add(BarcodeScannerPopup, {
                text: _t("Scan or fill in customer barcode to identify yourself"),
                getPayload: (code) => {
                    this.selfOrder._barcodePartnerAction({code: code});
                }
            });
            return;
        }
        // Open reward popup
        this.dialog.add(SelectRewardPopup, {
            getPayload: (reward) => {
                this.selfOrder.applyRewardFromReward(reward);
            },
            rewardType: "product",
        });
    }

    getPartnerLoyaltyPoints() {
        const cards = this.selfOrder.getLoyaltyCards();
        if (cards.length > 0) {
            return this.selfOrder.getProgramPointsString(cards[0].program_id);
        }
        return false;
    }
}
