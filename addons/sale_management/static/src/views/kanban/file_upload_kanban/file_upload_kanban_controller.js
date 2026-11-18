import { SaleFileUploadKanbanController } from '@sale/views/kanban/sale_file_upload_kanban/sale_file_upload_kanban_controller';
import { SaleTemplateDropdown } from '@sale_management/components/template_dropdown/template_dropdown';
import { patch } from '@web/core/utils/patch';

patch(SaleFileUploadKanbanController, {
    components: {
        ...SaleFileUploadKanbanController.components,
        SaleTemplateDropdown,
    },
});
