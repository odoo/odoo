import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { SaleFileUploadListController } from './sale_file_upload_list_controller';
import { SaleFileUploadListRenderer } from './sale_file_upload_list_renderer';

export const saleFileUploadListView = {
    ...listView,
    Controller: SaleFileUploadListController,
    Renderer: SaleFileUploadListRenderer,
};

registry.category('views').add('sale_file_upload_list', saleFileUploadListView);
