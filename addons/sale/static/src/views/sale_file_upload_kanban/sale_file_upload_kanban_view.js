import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { SaleFileUploadKanbanController } from './sale_file_upload_kanban_controller';
import { SaleFileUploadKanbanRenderer } from './sale_file_upload_kanban_renderer';

export const saleFileUploadKanbanView = {
    ...kanbanView,
    Controller: SaleFileUploadKanbanController,
    Renderer: SaleFileUploadKanbanRenderer,
};

registry.category('views').add('sale_file_upload_kanban', saleFileUploadKanbanView);
