import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { FileUploadListController } from "./file_upload_list_controller";
import { FileUploadListRenderer } from "./file_upload_list_renderer";

export const fileUploadListView = {
    ...listView,
    Controller: FileUploadListController,
    Renderer: FileUploadListRenderer,
    buttonTemplate: "account.FileuploadListView.Buttons",
};

registry.category("views").add("file_upload_list", fileUploadListView);
