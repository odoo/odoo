import { SaleFileUploadListController } from '@sale/views/list/sale_file_upload_list/sale_file_upload_list_controller';
import { SaleTemplateDropdown } from '@sale_management/components/template_dropdown/template_dropdown';
import { patch } from '@web/core/utils/patch';

patch(SaleFileUploadListController, {
    components: {
        ...SaleFileUploadListController.components,
        SaleTemplateDropdown,
    },
});
