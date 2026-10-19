import { Record, fields } from "@mail/model/export";

export class HrEmployee extends Record {
    static _name = "hr.employee";

    /** @type {Boolean} */
    active;
    /** @type {number} */
    id;
    /** @type {number} */
    company_id = fields.One("res.company");
    currency_id = fields.One("res.currency");
    department_id = fields.One("hr.department");
    employee_type_id = fields.One("hr.employee.type");
    /** @type {string} */
    first_contract_date;
    /** @type {string} */
    hr_icon_display;
    /** @type {string} */
    job_title;
    /** @type {string} */
    name;
    resource_id = fields.One("resource.resource", { inverse: "employee_id" });
    /** @type {boolean} */
    show_hr_icon_display;
    work_contact_id = fields.One("res.partner");
    user_id = fields.One("res.users");
    /** @type {string} */
    work_email;
    work_location_id = fields.One("hr.work.location");
    /** @type {string} */
    work_location_type;
    /** @type {string} */
    work_phone;
}

HrEmployee.register();
