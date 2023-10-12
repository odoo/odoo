/** @odoo-module **/

import { registry } from "@web/core/registry";
import { hierarchyView } from "../hierarchy/hierarchy_view";
import { HrEmployeeHierarchyRenderer } from "./hr_employee_hierarchy_renderer";

export const hrEmployeeHierarchyView = {
    ...hierarchyView,
    Renderer: HrEmployeeHierarchyRenderer,
};

registry.category("views").add("hr_employee_hierarchy", hrEmployeeHierarchyView);
