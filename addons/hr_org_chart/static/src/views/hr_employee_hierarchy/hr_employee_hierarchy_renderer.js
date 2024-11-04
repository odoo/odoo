import { Avatar } from "@mail/views/web/fields/avatar/avatar";

import { HierarchyRenderer } from "@web_hierarchy/hierarchy_renderer";
import { HrEmployeeHierarchyCard } from "./hr_employee_hierarchy_card";

export class HrEmployeeHierarchyRenderer extends HierarchyRenderer {
    static template = "hr_org_chart.HrEmployeeHierarchyRenderer";
    static components = {
        ...HierarchyRenderer.components,
        HierarchyCard: HrEmployeeHierarchyCard,
        Avatar,
    };
}
