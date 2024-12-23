import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
import { useSortable } from "@web/core/utils/sortable_owl";
import { onWillRender } from "@odoo/owl";

export class PosListRenderer extends ListRenderer {
    setup() {
        super.setup();
        onWillRender(() => {
            this.withHandleColumn = this.columns.some((col) =>
                ["handle", "handle_widget"].includes(col.widget)
            );
        });
        let dataRowId;
        useSortable({
            enable: () => this.canResequenceRows,
            // Params
            ref: this.rootRef,
            elements: ".o_row_draggable",
            handle_widget: ".o_handle_cell",
            cursor: "grabbing",
            placeholderClasses: ["d-table-row"],
            // Hooks
            onDragStart: (params) => {
                const { element } = params;
                dataRowId = element.dataset.id;
                return this.sortStart(params);
            },
            onDragEnd: (params) => this.sortStop(params),
            onDrop: (params) => this.sortDrop(dataRowId, params),
        });
    }
}

export const PosListView = {
    ...listView,
    Renderer: PosListRenderer,
};

registry.category("views").add("pos_list_renderer", PosListView);
