import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { RewardButton } from "@pos_self_order_loyalty/app/components/reward_button/reward_button";
import { SelectRewardPopup } from "@pos_self_order_loyalty/app/components/popup/select_reward_popup/select_reward_popup";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { signal } from "@odoo/owl";
import { roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";

patch(CartPage, {
    components: { ...CartPage.components, RewardButton },
});

patch(CartPage.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.barcodeReader = useService("barcode_reader");
        this.discountAsked = false;
        this.code = signal("");
        this.showCode = signal(false);
        this.applyCode = useTrackedAsync(this.applyCode.bind(this));
        this.selfOrder.currentOrder.recomputeRewards();
    },

    roundPoints(points) {
        return roundPrecision(points, 0.01);
    },

    async pay() {
        if (!this.discountAsked && this.selfOrder.currentOrder.getPartner()) {
            const discountReward = this.selfOrder.getLoyaltyPrograms("discount", true);
            this.discountAsked = true;
            if (Object.keys(discountReward).length > 0) {
                this.dialog.add(SelectRewardPopup, {
                    getPayload: (reward) => {
                        this.selfOrder.applyReward(reward);
                    },
                    rewardType: "discount",
                    claimableOnly: true,
                });
                return;
            }
        }
        await super.pay();
    },
    async applyCode() {
        if (!this.code()) {
            return;
        }
        const result = await this.selfOrder.applyCode(this.code());
        this.code.set("");
        if (result === true) {
            this.notification.add(_t("Code applied successfully."), {
                type: "success",
            });
        }
    },
    onKeydownCodeInput(ev) {
        if (ev.key.toUpperCase() === "ENTER") {
            this.applyCode.call();
        }
    },
    onClickShowCode() {
        this.showCode.set(!this.showCode());
    },
    canChangeQuantity(line, increase) {
        const result = super.canChangeQuantity(...arguments);
        if (line.is_reward_line && increase) {
            if (line.reward_id.reward_type === "discount") {
                return false;
            }
            if (line.reward_id.reward_type === "product") {
                const reward = line.reward_id;
                const points =
                    line.reward_id.program_id.getEarnedPoints(this.selfOrder.currentOrder) +
                    line.reward_id.program_id.getAvailablePoints(this.selfOrder.currentOrder);
                const claimableCount = reward.clear_wallet
                    ? 1
                    : Math.floor(points / reward.required_points);
                if (line.qty + 1 > reward.reward_product_qty * claimableCount) {
                    return false;
                }
            }
        }
        return result;
    },
    changeQuantity(line, increase) {
        super.changeQuantity(...arguments);
        this.selfOrder.currentOrder.recomputeRewards();
    },
    doRemoveLine(line) {
        super.doRemoveLine(...arguments);
        this.selfOrder.currentOrder.recomputeRewards();
    },
    get displayBeforeDiscount() {
        return this.selfOrder.currentOrder.lines.find(
            (line) => line.is_reward_line && line.reward_id.reward_type === "discount"
        );
    },
    getTotalDiscount() {
        return this.selfOrder.currentOrder.lines.reduce((total, line) => {
            if (line.is_reward_line && line.reward_id.reward_type === "discount") {
                return total + line.priceIncl;
            }
            return total;
        }, 0);
    },
    getLoyaltyProgramClass(program) {
        return program.uiState.pointsDifference > 0 ? "text-success" : "text-danger";
    },
    async openMobileScanner() {
        if (!isBarcodeScannerSupported() && this.barcodeReader) {
            return;
        }
        let data;
        try {
            data = await scanBarcode(this.env);
        } catch (error) {
            // Here, we know the structure of the error raised by BarcodeScanner.
            this.dialog.add(AlertDialog, {
                title: _t("Unable to scan"),
                body: error?.message || error?.error?.message || "Unable to find barcode scanner.",
            });
            return;
        }
        if (data) {
            this.barcodeReader.scan(data);
            if ("vibrate" in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.notification.add(_t("Please, Scan again!"), {
                type: "warning",
            });
        }
    },
});
