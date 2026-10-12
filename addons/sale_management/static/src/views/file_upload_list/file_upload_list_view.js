import { saleFileUploadListView } from '@sale/views/sale_file_upload_list/sale_file_upload_list_view';
import { patch } from '@web/core/utils/patch';

patch(saleFileUploadListView, {
    buttonTemplate: 'sale_management.SaleManagementTemplateListView.Buttons',
});
