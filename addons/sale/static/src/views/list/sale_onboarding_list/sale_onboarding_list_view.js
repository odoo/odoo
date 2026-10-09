import { registry } from "@web/core/registry";
import { saleFileUploadListView } from '../sale_file_upload_list/sale_file_upload_list_view';
import { SaleListRenderer } from "./sale_onboarding_list_renderer";

export const SaleListView = {
    ...saleFileUploadListView,
    Renderer: SaleListRenderer,
};

registry.category("views").add("sale_onboarding_list", SaleListView);
