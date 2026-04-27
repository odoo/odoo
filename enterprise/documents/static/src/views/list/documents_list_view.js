/** @odoo-module **/

import { registry } from "@web/core/registry";

import { listView } from "@web/views/list/list_view";
import { DocumentsControlPanel } from "../search/documents_control_panel";
import { DocumentsListController } from "./documents_list_controller";
import { DocumentsListModel } from "./documents_list_model";
import { DocumentsListRenderer } from "./documents_list_renderer";
import { DocumentsSearchModel } from "../search/documents_search_model";
import { DocumentsSearchPanel } from "../search/documents_search_panel";


export const DocumentsListView = Object.assign({}, listView, {
    SearchModel: DocumentsSearchModel,
    SearchPanel: DocumentsSearchPanel,
    ControlPanel: DocumentsControlPanel,
    Controller: DocumentsListController,
    Model: DocumentsListModel,
    Renderer: DocumentsListRenderer,
    searchMenuTypes: ["filter", "groupBy", "favorite"],
});

registry.category("views").add("documents_list", DocumentsListView);
