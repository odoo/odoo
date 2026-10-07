import { registry } from "@web/core/registry";
import { saleOrderListView } from '../sale_order_list/sale_order_list_view';

export const saleListView = {
    ...saleOrderListView,
};

registry.category("views").add("sale_onboarding_list", saleListView);
