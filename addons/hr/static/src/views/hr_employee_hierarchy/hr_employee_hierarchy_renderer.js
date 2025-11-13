import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { useService } from "@web/core/utils/hooks";

import { HierarchyRenderer } from "@web_hierarchy/hierarchy_renderer";
import { HrEmployeeHierarchyCard } from "./hr_employee_hierarchy_card";

export class HrEmployeeHierarchyRenderer extends HierarchyRenderer {
    static template = "hr.HrEmployeeHierarchyRenderer";
    static components = {
        ...HierarchyRenderer.components,
        HierarchyCard: HrEmployeeHierarchyCard,
        Avatar,
    };

    setup() {
        super.setup();
        this.action = useService("action");
    }

    get employeesInCycleIds() {
        return this.props.model.nodesInCycle;
    }

    _displayEmployeesInCycle() {
        const { model } = this.props;
        const resModel = model.resModel;

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            domain: [["id", "in", this.employeesInCycleIds]],
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }
}
