import { saleFileUploadKanbanView } from '@sale/views/sale_file_upload_kanban/sale_file_upload_kanban_view';
import { patch } from '@web/core/utils/patch';

patch(saleFileUploadKanbanView, {
    buttonTemplate: 'sale_management.SaleManagementTemplateKanbanView.Buttons',
});
