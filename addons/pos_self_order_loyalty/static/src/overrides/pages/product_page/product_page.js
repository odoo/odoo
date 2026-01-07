import { ProductPage } from "@pos_self_order/app/pages/product_page/product_page";
import { patch } from "@web/core/utils/patch";

patch(ProductPage, {
    props: { ...ProductPage.props, reward_id: { type: Object, optional: true }, card_id: { type: Object, optional: true }, code: { type: String, optional: true } },
});

patch(ProductPage.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.isValidReward) {
            // The reward is not valid for the selected loyalty card, go back to avoid issues.
            this.router.navigate("product_list");
        }
        if (this.props.reward_id && this.props.reward_id.reward_type === 'product') {
            this.state.qty = this.props.reward_id.reward_product_qty;
        }
    },
    get isValidReward() {
        return this.props.card_id?.program_id.id == this.props.reward_id?.program_id.id;
    },
    get addToOrderOpts() {
        let opts = super.addToOrderOpts;
        if (this.props.reward_id && this.props.card_id) {
            opts = {
                ...opts,
                ...this.selfOrder.getRewardOpts(this.props.reward_id, this.props.card_id)
            }
        }
        return opts;
    },
    get addToOrderUiState() {
        let uiState = super.addToOrderUiState;
        if (this.props.code) {
            uiState = {
                ...uiState,
                rewardCode: this.props.code,
            }
        }
        return uiState;
    },
    canChangeQuantity() {
        const result = super.canChangeQuantity(...arguments);
        if (this.props.reward_id && this.props.reward_id.reward_type === 'product') {
            return false;
        }
        return result;
    },
});
