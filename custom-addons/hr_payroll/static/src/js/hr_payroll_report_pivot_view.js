/** @odoo-module **/

import { HrPayrollReportPivotModel } from "./hr_payroll_report_pivot_model";
import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

const hrPayrollPivotView = {...pivotView, Model: HrPayrollReportPivotModel};
viewRegistry.add("hr_payroll_report_pivot", hrPayrollPivotView);
