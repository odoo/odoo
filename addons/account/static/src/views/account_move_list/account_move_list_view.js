import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { AccountMoveListController } from "./account_move_list_controller";
import { AccountUploadListRenderer } from "../account_upload_list/account_upload_list_renderer";

export const accountMoveUploadListView = {
    ...listView,
    Controller: AccountMoveListController,
    Renderer: AccountUploadListRenderer,
};

registry.category("views").add("account_tree", accountMoveUploadListView);
