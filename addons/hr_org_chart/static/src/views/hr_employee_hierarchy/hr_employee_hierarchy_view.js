/** @odoo-module **/

import { registry } from "@web/core/registry";
import { hierarchyView } from "@web_hierarchy/hierarchy_view";
import { HrEmployeeHierarchyRenderer } from "./hr_employee_hierarchy_renderer";
import { HierarchyController } from "@web_hierarchy/hierarchy_controller";
import { HrActionHelper } from "@hr/views/hr_action_helper";

export class HrEmployeeHierarchyController extends HierarchyController {
    static template = "hr_org_chart.HierarchyView";
    static components = { ...HierarchyController.components, HrActionHelper };
}

export const hrEmployeeHierarchyView = {
    ...hierarchyView,
    Controller: HrEmployeeHierarchyController,
    Renderer: HrEmployeeHierarchyRenderer,
};

registry.category("views").add("hr_employee_hierarchy", hrEmployeeHierarchyView);
