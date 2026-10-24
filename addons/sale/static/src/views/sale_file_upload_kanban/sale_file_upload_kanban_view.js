import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { SaleFileUploadKanbanController } from './sale_file_upload_kanban_controller';

export const saleFileUploadKanbanView = {
    ...kanbanView,
    Controller: SaleFileUploadKanbanController,
};

registry.category('views').add('sale_file_upload_kanban', saleFileUploadKanbanView);
