import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import { DynamicGroupList } from "@web/model/relational_model/dynamic_group_list";

export class StockKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
    }

    // If all Inventory Overview graphs are empty, we use random sample data
    getGroupsOrRecords() {
        const { list } = this.props;
        let records = [];
        if (list instanceof DynamicRecordList) {
            records.push(...list.records);
        } else if (list instanceof DynamicGroupList) {
            list.groups.forEach(g => {
                records.push(...g.list.records);
            });
        }
        // Data type "sample" is assigned in Python to empty graph data
        let allEmpty = records.every(r => {
            return r.data.kanban_dashboard_graph.includes('"type": "sample"');
        });
        if (allEmpty) {
            records.forEach(r => {
                let parsedDashboardData = JSON.parse(r.data.kanban_dashboard_graph);
                parsedDashboardData[0].values.forEach(d => {
                    d.value = Math.floor(Math.random() * 9 + 1);
                });
                r.data.kanban_dashboard_graph = JSON.stringify(parsedDashboardData);
            });
        }
        return super.getGroupsOrRecords();
    }
}

export const StockKanbanView = {
    ...kanbanView,
    Renderer: StockKanbanRenderer,
};

registry.category("views").add("stock_dashboard_kanban", StockKanbanView);
