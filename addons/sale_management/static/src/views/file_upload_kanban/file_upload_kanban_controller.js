import { SaleFileUploadKanbanController } from '@sale/views/sale_file_upload_kanban/sale_file_upload_kanban_controller';
import { SaleTemplateDropdown } from '@sale_management/views/components/template_dropdown';
import { patch } from '@web/core/utils/patch';

patch(SaleFileUploadKanbanController, {
    components: {
        ...SaleFileUploadKanbanController.components,
        SaleTemplateDropdown,
    },
});
