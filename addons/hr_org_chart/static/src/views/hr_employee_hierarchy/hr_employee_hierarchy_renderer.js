/** @odoo-module **/

import { Avatar } from "@mail/views/web/fields/avatar/avatar";

import { HierarchyRenderer } from "@web_hierarchy/hierarchy_renderer";

export class HrEmployeeHierarchyRenderer extends HierarchyRenderer {
   static template = "hr_org_chart.HrEmployeeHierarchyRenderer";
   static components = {
      ...HierarchyRenderer.components,
      Avatar,
   };
}
