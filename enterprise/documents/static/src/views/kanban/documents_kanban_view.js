/** @odoo-module **/

import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { DocumentsControlPanel } from "../search/documents_control_panel";
import { DocumentsKanbanController } from "./documents_kanban_controller";
import { DocumentsKanbanModel } from "./documents_kanban_model";
import { DocumentsKanbanRenderer } from "./documents_kanban_renderer";
import { DocumentsSearchModel } from "../search/documents_search_model";
import { DocumentsSearchPanel } from "../search/documents_search_panel";
import { DocumentsKanbanArchParser } from "./documents_kanban_arch_parser";


export const DocumentsKanbanView = Object.assign({}, kanbanView, {
    ArchParser: DocumentsKanbanArchParser,
    SearchModel: DocumentsSearchModel,
    SearchPanel: DocumentsSearchPanel,
    ControlPanel: DocumentsControlPanel,
    Controller: DocumentsKanbanController,
    Model: DocumentsKanbanModel,
    Renderer: DocumentsKanbanRenderer,
    searchMenuTypes: ["filter", "groupBy", "favorite"],
});

registry.category("views").add("documents_kanban", DocumentsKanbanView);
