declare module "models" {
    import { HrDepartment as HrDepartmentClass } from "@hr/core/common/hr_department_model";
    import { HrJob as HrJobClass } from "@hr/core/common/hr_job_model";
    import { HrEmployee as HrEmployeeClass } from "@hr/core/common/hr_employee_model";
    import { HrEmployeePublic as HrEmployeePublicClass } from "@hr/core/common/hr_employee_public_model";
    import { HrEmployeeType as HrEmployeeTypeClass } from "@hr/core/common/hr_employee_type_model";
    import { HrWorkLocation as HrWorkLocationClass } from "@hr/core/common/hr_work_location_model";

    export interface HrDepartment extends HrDepartmentClass {}
    export interface HrJob extends HrJobClass {}
    export interface HrEmployee extends HrEmployeeClass {}
    export interface HrEmployeePublic extends HrEmployeePublicClass {}
    export interface HrEmployeeType extends HrEmployeeTypeClass {}
    export interface HrWorkLocation extends HrWorkLocationClass {}

    export interface ResourceResource {
        department_id: HrDepartment;
        job_id: HrJob;
        employee_id: HrEmployee[];
    }
    export interface ResPartner {
        employee_id: HrEmployee;
        employee_ids: HrEmployee[];
        employeeId: number|undefined;
    }
    export interface ResUsers {
        all_employee_ids: HrEmployee[];
        employee_id: HrEmployee;
    }
    export interface Store {
        getRelevantEmployee: (employees: HrEmployee[]) => unknown;
        "hr.department": StaticMailRecord<HrDepartment, typeof HrDepartmentClass>;
        "hr.job": StaticMailRecord<HrJob, typeof HrJobClass>;
        "hr.employee": StaticMailRecord<HrEmployee, typeof HrEmployeeClass>;
        "hr.employee.public": StaticMailRecord<HrEmployeePublic, typeof HrEmployeePublicClass>;
        "hr.employee.type": StaticMailRecord<HrEmployeeType, typeof HrEmployeeTypeClass>;
        "hr.work.location": StaticMailRecord<HrWorkLocation, typeof HrWorkLocationClass>;
    }

    export interface Models {
        "hr.department": HrDepartment;
        "hr.job": HrJob;
        "hr.employee": HrEmployee;
        "hr.employee.public": HrEmployeePublic;
        "hr.employee.type": HrEmployeeType;
        "hr.work.location": HrWorkLocation;
    }
}
