import { SaleOrderFormStaticList } from "@sale/views/sale_order_form_view/sale_order_static_list";
import { patch } from "@web/core/utils/patch";

patch(SaleOrderFormStaticList.prototype, {
    shouldPropagateQuantity(line, sectionRecord) {
        return super.shouldPropagateQuantity(line, sectionRecord) && !line.data.is_reward_line;
    },
});
