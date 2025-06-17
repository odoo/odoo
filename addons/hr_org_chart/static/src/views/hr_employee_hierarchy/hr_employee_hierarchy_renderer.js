import { Avatar } from "@mail/views/web/fields/avatar/avatar";

import { HierarchyRenderer } from "@web_hierarchy/hierarchy_renderer";
import { HrEmployeeHierarchyCard } from "./hr_employee_hierarchy_card";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class HrEmployeeHierarchyRenderer extends HierarchyRenderer {
    static template = "hr_org_chart.HrEmployeeHierarchyRenderer";
    static components = {
        ...HierarchyRenderer.components,
        HierarchyCard: HrEmployeeHierarchyCard,
        Avatar,
    };

    setup() {
        super.setup();
        this.actionHelperService = useService("hr_action_helper");
        onWillStart(async () => {
            this.showActionHelper = await this.actionHelperService.showActionHelper();
        });
    }
}
