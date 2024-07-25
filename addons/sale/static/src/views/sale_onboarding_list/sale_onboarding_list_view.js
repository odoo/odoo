import { registry } from "@web/core/registry";
import { fileUploadListView } from "@account/views/file_upload_list/file_upload_list_view";
import { SaleListRenderer } from "./sale_onboarding_list_renderer";

export const SaleListView = {
    ...fileUploadListView,
    Renderer: SaleListRenderer,
};

registry.category("views").add("sale_onboarding_list", SaleListView);
