import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models } from "@web/../tests/web_test_helpers";

export class PlanningSlot extends models.Model {
    _name = "planning.slot";

    name = fields.Char();
    start_datetime = fields.Datetime({ string: "Start Date Time" });
    end_datetime = fields.Datetime({ string: "End Date Time" });
    allocated_hours = fields.Float();
    allocated_percentage = fields.Float();
    role_id = fields.Many2one({ relation: "planning.role" });
    color = fields.Integer();
    repeat = fields.Boolean();
    recurrence_update = fields.Selection({
        selection: [
            ["this", "This shift"],
            ["subsequent", "This and following shifts"],
            ["all", "All shifts"],
        ],
    });
    resource_id = fields.Many2one({ relation: "resource.resource" });
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["published", "Published"],
        ],
    });
    department_id = fields.Many2one({ relation: "hr.department" });
    employee_id = fields.Many2one({ relation: "hr.employee" });
    role_ids = fields.One2many({ relation: "planning.role" });
    resource_type = fields.Selection({
        selection: [
            ["user", "Human"],
            ["material", "Material"],
        ],
    });
    user_id = fields.Many2one({ relation: "res.users" });
    conflicting_slot_ids = fields.Many2many({ relation: "planning.slot" });
    resource_color = fields.Integer({ related: 'resource_id.color' })
}

export class ResourceResource extends models.Model {
    _name = "resource.resource";

    name = fields.Char();
    resource_type = fields.Selection({
        selection: [
            ["user", "Human"],
            ["material", "Material"],
        ],
    });
    role_ids = fields.One2many({ relation: "planning.role" });
    employee_id = fields.Many2one({ relation: "hr.employee" });
    user_id = fields.Many2one({ relation: "res.users" });
    im_status = fields.Char();
    color = fields.Integer();
}

export class PlanningRole extends models.Model {
    _name = "planning.role";

    name = fields.Char();
    color = fields.Integer();
}

export class HrEmployee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();
    user_id = fields.Many2one({ relation: "res.users" });
    partner_id = fields.Many2one({ relation: "res.partner" });
    resource_id = fields.Many2one({ relation: "resource.resource" });
    user_partner_id = fields.Many2one({ relation: "res.partner" });
}

export class HrEmployeePublic extends models.Model {
    _name = "hr.employee.public";

    name = fields.Char();
    user_id = fields.Many2one({ relation: "res.users" });
    partner_id = fields.Many2one({ relation: "res.partner" });
    resource_id = fields.Many2one({ relation: "resource.resource" });
    user_partner_id = fields.Many2one({ relation: "res.partner" });
}

export class HrDepartment extends models.Model {
    _name = "hr.department";

    name = fields.Char();
}

export const planningModels = {
    PlanningSlot,
    ResourceResource,
    PlanningRole,
    HrEmployee,
    HrEmployeePublic,
    HrDepartment,
};

export function definePlanningModels() {
    defineMailModels();
    defineModels(planningModels);
}
