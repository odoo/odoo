import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();

    _records = [{ id: 1, name: "Employee 1" }];
}

export class ProductProduct extends models.Model {
    _name = "product.product";

    name = fields.Char();
    type = fields.Selection({
        string: "Type",
        selection: [("consu", "Goods"), ("service", "Service"), ("combo", "Combo")],
    });

    _records = [
        { id: 1, name: "Service Product 1", type: "service" },
        { id: 2, name: "Consumable Product 1", type: "consu" },
        { id: 3, name: "Service Product 2", type: "service" },
    ];
}

export class SaleOrder extends models.Model {
    _name = "sale.order";

    name = fields.Char({ string: "name" });
    partner_id = fields.Many2one({ string: "Customer", relation: "res.partner" });
    project_id = fields.Many2one({ string: "Project", relation: "project.project" });
    order_line = fields.One2many({ relation: "sale.order.line" });

    _records = [{ id: 1, name: "Sales Order 1" }];
}

export class SaleOrderLine extends models.Model {
    _name = "sale.order.line";

    name = fields.Char({ related: "product_id.name" });
    product_id = fields.Many2one({ string: "Product", relation: "product.product" });

    _records = [{ id: 1, product_id: 1 }];
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
