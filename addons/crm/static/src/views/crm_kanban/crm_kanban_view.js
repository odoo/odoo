import { registry } from "@web/core/registry";
import { CrmKanbanModel } from "@crm/views/crm_kanban/crm_kanban_model";
import { CrmKanbanArchParser } from "@crm/views/crm_kanban/crm_kanban_arch_parser";
import { CrmKanbanRenderer } from "@crm/views/crm_kanban/crm_kanban_renderer";
import { rottingKanbanView } from "@mail/js/rotting_mixin/rotting_kanban_view";

export const crmKanbanView = {
    ...rottingKanbanView,
    ArchParser: CrmKanbanArchParser,
    // Makes it easier to patch
    Controller: class extends rottingKanbanView.Controller {
        get progressBarAggregateFields() {
            const res = super.progressBarAggregateFields;
            const progressAttributes = this.props.archInfo.progressAttributes;
            if (progressAttributes && progressAttributes.recurring_revenue_sum_field) {
                res.push(progressAttributes.recurring_revenue_sum_field);
            }
            return res;
        }
    },
    Model: CrmKanbanModel,
    Renderer: CrmKanbanRenderer,
};

registry.category("views").add("crm_kanban", crmKanbanView);
