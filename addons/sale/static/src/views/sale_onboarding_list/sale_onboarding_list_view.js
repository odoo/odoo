import { registry } from "@web/core/registry";
import { saleFileUploadListView } from '../sale_file_upload_list/sale_file_upload_list_view';

export const SaleListView = {
    ...saleFileUploadListView,
};

registry.category("views").add("sale_onboarding_list", SaleListView);
