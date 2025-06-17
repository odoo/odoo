import { HierarchyController } from "@web_hierarchy/hierarchy_controller";
import { patchHrEmployee } from "@hr/views/patch_hr_employee";

export class HrEmployeeHierarchyController extends HierarchyController {
    static template = "hr_org_chart.HierarchyView";
}
patchHrEmployee(HrEmployeeHierarchyController);
