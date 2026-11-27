import { saleOrderKanbanView } from '@sale/views/sale_order_kanban/sale_order_kanban_view';
import { patch } from '@web/core/utils/patch';

patch(saleOrderKanbanView, {
    buttonTemplate: 'sale_management.SaleManagementTemplateKanbanView.Buttons',
});
