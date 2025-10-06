import { registry } from "@web/core/registry";

import { hierarchyView } from "@web_hierarchy/hierarchy_view";
import { HrEmployeeHierarchyRenderer } from "./hr_employee_hierarchy_renderer";
import { HrEmployeeHierarchyModel } from "./hr_employee_hierarchy_model";

export const hrEmployeeHierarchyView = {
    ...hierarchyView,
    Renderer: HrEmployeeHierarchyRenderer,
    Model: HrEmployeeHierarchyModel,
};

registry.category("views").add("hr_employee_hierarchy", hrEmployeeHierarchyView);
