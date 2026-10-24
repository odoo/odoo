import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { SaleFileUploadListController } from './sale_file_upload_list_controller';

export const saleFileUploadListView = {
    ...listView,
    Controller: SaleFileUploadListController,
};

registry.category('views').add('sale_file_upload_list', saleFileUploadListView);
