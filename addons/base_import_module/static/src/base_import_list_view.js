import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ImportModuleListRenderer } from "./base_import_list_renderer";


export const ImportModuleListView = {
    ...listView,
    Renderer: ImportModuleListRenderer,
}

registry.category("views").add("ir_module_module_tree_view", ImportModuleListView);
