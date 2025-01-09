import { mailModels } from "@mail/../tests/mail_test_helpers";
import { ProductProduct, SaleOrder, SaleOrderLine } from "@sale_project/../tests/project_task_model";
import { defineModels, fields, models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();

    _records = [{ id: 1, name: "Employee 1" }];
}

export class ProjectSaleLineEmployeeMap extends models.Model {
    _name = "project.sale.line.employee.map";

    project_id = fields.Many2one({ relation: "project.project" });
    sale_line_id = fields.Many2one({ string: "Sales Order Item", relation: "sale.order.line" });
    employee_id = fields.Many2one({ string: "Employee", relation: "hr.employee" });
    price_unit = fields.Float({ string: "Unit Price" });

    _records = [{ id: 1, project_id: 1, employee_id: 1, sale_line_id: 1, price_unit: 200.0 }];
}

export class ProjectProject extends models.Model {
    _name = "project.project";

    name = fields.Char();
    sale_line_employee_ids = fields.One2many({ relation: "project.sale.line.employee.map" });

    _records = [{ id: 1, name: "Billable Project", sale_line_employee_ids: [1] }];
}

export const saleTimesheetModels = {
    ProjectProject,
    SaleOrderLine,
    ProjectSaleLineEmployeeMap,
    HrEmployee,
    SaleOrder,
    ProductProduct,
};

export function defineSaleTimesheetModels() {
    return defineModels({ ...mailModels, ...saleTimesheetModels });
}
