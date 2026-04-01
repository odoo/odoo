declare module "models" {
    import { HrDepartment as HrDepartmentClass } from "@hr/core/common/hr_department_model";
    import { HrEmployee as HrEmployeeClass } from "@hr/core/common/hr_employee_model";
    import { HrWorkLocation as HrWorkLocationClass } from "@hr/core/common/hr_work_location_model";

    export interface HrDepartment extends HrDepartmentClass {}
    export interface HrEmployee extends HrEmployeeClass {}
    export interface HrWorkLocation extends HrWorkLocationClass {}

    export interface ResPartner {
        employee_id: HrEmployee;
        employee_ids: HrEmployee[];
        employeeId: number|undefined;
    }
    export interface ResUsers {
        employee_id: HrEmployee;
        employee_ids: HrEmployee[];
    }
    export interface Store {
        "hr.department": StaticMailRecord<HrDepartment, typeof HrDepartmentClass>;
        "hr.employee": StaticMailRecord<HrEmployee, typeof HrEmployeeClass>;
        "hr.work.location": StaticMailRecord<HrWorkLocation, typeof HrWorkLocationClass>;
    }

    export interface Models {
        "hr.department": HrDepartment;
        "hr.employee": HrEmployee;
        "hr.work.location": HrWorkLocation;
    }
}
