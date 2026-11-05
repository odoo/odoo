import { registry } from "@web/core/registry";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { FidelityRuleRewardKanbanRecord } from "./fidelity_rule_reward_kanban_record_view";

export class FidelityRuleRewardKanbanRenderer extends KanbanRenderer {
    static template = "fidelity.FidelityRuleRewardKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: FidelityRuleRewardKanbanRecord,
    };
}

export const FidelityRuleRewardKanbanView = {
    ...kanbanView,
    Renderer: FidelityRuleRewardKanbanRenderer,
};

registry.category("views").add("fidelity_rule_reward_kanban_view", FidelityRuleRewardKanbanView);
