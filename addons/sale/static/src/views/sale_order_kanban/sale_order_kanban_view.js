import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { SaleOrderKanbanController } from './sale_order_kanban_controller';

export const saleOrderKanbanView = {
    ...kanbanView,
    Controller: SaleOrderKanbanController,
};

registry.category('views').add('sale_order_kanban', saleOrderKanbanView);
