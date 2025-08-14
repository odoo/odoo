import { registry } from "@web/core/registry";

import { hierarchyView } from "@web_hierarchy/hierarchy_view";
import { HrEmployeeHierarchyRenderer } from "./hr_employee_hierarchy_renderer";
import { HrEmployeeHierarchyController } from "./hr_employee_hierarchy_controller";

export const hrEmployeeHierarchyView = {
    ...hierarchyView,
    Renderer: HrEmployeeHierarchyRenderer,
    Controller: HrEmployeeHierarchyController,
};

registry.category("views").add("hr_employee_hierarchy", hrEmployeeHierarchyView);
