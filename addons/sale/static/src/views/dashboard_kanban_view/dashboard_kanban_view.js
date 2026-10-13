import { registry } from '@web/core/registry';
import { SaleFileUploadKanbanRenderer } from '../sale_file_upload_kanban/sale_file_upload_kanban_renderer';
import { saleFileUploadKanbanView } from '../sale_file_upload_kanban/sale_file_upload_kanban_view';
import { Dashboard } from '../../js/dashboard/dashboard';

export class DashboardKanbanRenderer extends SaleFileUploadKanbanRenderer {
    static template = 'sale.KanbanRenderer';
    static components = {
        ...SaleFileUploadKanbanRenderer.components,
        Dashboard,
    };
}

export const dashboardKanbanView = Object.assign(Object.create(saleFileUploadKanbanView), {
    Renderer: DashboardKanbanRenderer,
});

registry.category('views').add('sale_dashboard_kanban', dashboardKanbanView);
