import { registry } from '@web/core/registry';
import { SaleKanbanRenderer } from '../sale_onboarding_kanban/sale_onboarding_kanban_renderer';
import { saleFileUploadKanbanView } from '../sale_file_upload_kanban/sale_file_upload_kanban_view';
import { Dashboard } from '../../js/dashboard/dashboard';

export class DashboardKanbanRenderer extends SaleKanbanRenderer {
    static template = 'sale.KanbanRenderer';
    static components = {
        ...SaleKanbanRenderer.components,
        Dashboard,
    };
}

export const dashboardKanbanView = Object.assign(Object.create(saleFileUploadKanbanView), {
    Renderer: DashboardKanbanRenderer,
});

registry.category('views').add('sale_dashboard_kanban', dashboardKanbanView);
