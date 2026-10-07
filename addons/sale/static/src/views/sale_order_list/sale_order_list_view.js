import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { SaleOrderListController } from './sale_order_list_controller';

export const saleOrderListView = {
    ...listView,
    Controller: SaleOrderListController,
};

registry.category('views').add('sale_order_list', saleOrderListView);
