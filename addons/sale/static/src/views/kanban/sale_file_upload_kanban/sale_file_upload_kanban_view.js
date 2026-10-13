import { registry } from '@web/core/registry';
import { fileUploadKanbanView } from '@account/views/file_upload_kanban/file_upload_kanban_view';
import { SaleFileUploadKanbanController } from './sale_file_upload_kanban_controller';
import { SaleFileUploadKanbanRenderer } from './sale_file_upload_kanban_renderer';

export const saleFileUploadKanbanView = {
    ...fileUploadKanbanView,
    Controller: SaleFileUploadKanbanController,
    Renderer: SaleFileUploadKanbanRenderer,
};

registry.category('views').add('sale_file_upload_kanban', saleFileUploadKanbanView);
