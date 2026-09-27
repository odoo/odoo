import { SaleFileUploadListController } from '@sale/views/sale_file_upload_list/sale_file_upload_list_controller';
import { SaleTemplateDropdown } from '@sale_management/views/components/template_dropdown';
import { patch } from '@web/core/utils/patch';

patch(SaleFileUploadListController, {
    components: {
        ...SaleFileUploadListController.components,
        SaleTemplateDropdown,
    },
});
