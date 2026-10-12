import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { PosSearchModel } from "@point_of_sale/backend/views/pos_search_model";

export const posListView = {
    ...listView,
    SearchModel: PosSearchModel,
};

registry.category("views").add("pos_list_view", posListView);
