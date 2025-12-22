import { registry } from "@web/core/registry";
import { fileUploadListView } from "../file_upload_list/file_upload_list_view";
import { AccountMoveListController } from "./account_move_list_controller";
import { AccountMoveListRenderer } from "./account_move_list_renderer";

export const accountMoveUploadListView = {
    ...fileUploadListView,
    Controller: AccountMoveListController,
    Renderer: AccountMoveListRenderer,
    buttonTemplate: "account.AccountMoveListView.Buttons",
};

registry.category("views").add("account_tree", accountMoveUploadListView);
