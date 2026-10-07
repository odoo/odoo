import { registry } from '@web/core/registry';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { saleOrderKanbanView } from '../sale_order_kanban/sale_order_kanban_view';
import { Dashboard } from '../../js/dashboard/dashboard';

export class DashboardKanbanRenderer extends KanbanRenderer {
    static template = 'sale.KanbanRenderer';
    static components = {
        ...KanbanRenderer.components,
        Dashboard,
    };
}

export const dashboardKanbanView = Object.assign(Object.create(saleOrderKanbanView), {
    Renderer: DashboardKanbanRenderer,
});

registry.category('views').add('sale_dashboard_kanban', dashboardKanbanView);
