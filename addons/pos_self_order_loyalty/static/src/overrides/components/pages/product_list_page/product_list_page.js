import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { patch } from "@web/core/utils/patch";
import { RewardButton } from "@pos_self_order_loyalty/app/components/reward_button/reward_button";

patch(ProductListPage, {
    components: { ...ProductListPage.components, RewardButton },
});
