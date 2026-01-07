import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";


export class LoyaltyReward extends Base {
    static pythonModel = "loyalty.reward";

    initState() {
        super.initState();
        this.uiState = {
            proposedToUser: false,
            ...this.uiState,
        };
    }

    get imageUrl() {
        if (this.reward_type === "product") {
            const product = this.reward_product_ids[0].product_tmpl_id
            return `/web/image/product.template/${product.id}/image_512?unique=${product.write_date}`;
        }
    }
}

registry.category("pos_available_models").add(LoyaltyReward.pythonModel, LoyaltyReward);