/** @odoo-module **/

import PosComponent from "@point_of_sale/js/PosComponent";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import Registries from "@point_of_sale/js/Registries";

export class eWalletButton extends PosComponent {
    _getEWalletRewards(order) {
        const claimableRewards = order.getClaimableRewards();
        const eWalletRewards = claimableRewards.filter(
            ({ reward }) => reward.program_id.program_type == "ewallet"
        );
        return eWalletRewards;
    }
    _getEWalletPrograms() {
        return this.env.pos.programs.filter((p) => p.program_type == "ewallet");
    }
    async _onClickWalletButton() {
        const order = this.env.pos.get_order();
        const eWalletPrograms = this.env.pos.programs.filter((p) => p.program_type == "ewallet");
        const orderTotal = order.get_total_with_tax();
        const eWalletRewards = this._getEWalletRewards(order);
        if (orderTotal < 0 && eWalletPrograms.length >= 1) {
            let selectedProgram = null;
            if (eWalletPrograms.length == 1) {
                selectedProgram = eWalletPrograms[0];
            } else {
                const { confirmed, payload } = await this.showPopup("SelectionPopup", {
                    title: this.env._t("Refund with eWallet"),
                    list: eWalletPrograms.map((program) => ({
                        id: program.id,
                        item: program,
                        label: program.name,
                    })),
                });
                if (confirmed) {
                    selectedProgram = payload;
                }
            }
            if (selectedProgram) {
                const eWalletProduct = this.env.pos.db.get_product_by_id(
                    selectedProgram.trigger_product_ids[0]
                );
                order.add_product(eWalletProduct, {
                    price: -orderTotal,
                    merge: false,
                    eWalletGiftCardProgram: selectedProgram,
                });
            }
        } else if (eWalletRewards.length >= 1) {
            let eWalletReward = null;
            if (eWalletRewards.length == 1) {
                eWalletReward = eWalletRewards[0];
            } else {
                const { confirmed, payload } = await this.showPopup("SelectionPopup", {
                    title: this.env._t("Use eWallet to pay"),
                    list: eWalletRewards.map(({ reward, coupon_id }) => ({
                        id: reward.id,
                        item: { reward, coupon_id },
                        label: `${reward.description} (${reward.program_id.name})`,
                    })),
                });
                if (confirmed) {
                    eWalletReward = payload;
                }
            }
            if (eWalletReward) {
                const result = order._applyReward(
                    eWalletReward.reward,
                    eWalletReward.coupon_id,
                    {}
                );
                if (result !== true) {
                    // Returned an error
                    this.showPopup("ErrorPopup", {
                        title: this.env._t("Error"),
                        body: result,
                    });
                }
                order._updateRewards();
            }
        }
    }
    _shouldBeHighlighted(orderTotal, eWalletPrograms, eWalletRewards) {
        return (orderTotal < 0 && eWalletPrograms.length >= 1) || eWalletRewards.length >= 1;
    }
    _getText(orderTotal, eWalletPrograms, eWalletRewards) {
        if (orderTotal < 0 && eWalletPrograms.length >= 1) {
            return this.env._t("eWallet Refund");
        } else if (eWalletRewards.length >= 1) {
            return this.env._t("eWallet Pay");
        } else {
            return this.env._t("eWallet");
        }
    }
}
eWalletButton.template = "point_of_sale.eWalletButton";

ProductScreen.addControlButton({
    component: eWalletButton,
    condition: function () {
        return this.env.pos.programs.filter((p) => p.program_type == "ewallet").length > 0;
    },
});

Registries.Component.add(eWalletButton);
