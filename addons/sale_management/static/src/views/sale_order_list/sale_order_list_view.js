import { saleOrderListView } from '@sale/views/sale_order_list/sale_order_list_view';
import { patch } from '@web/core/utils/patch';

patch(saleOrderListView, {
    buttonTemplate: 'sale_management.SaleManagementTemplateListView.Buttons',
});
