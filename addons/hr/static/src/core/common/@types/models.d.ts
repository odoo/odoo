declare module "models" {
    import { HrEmployee as HrEmployeeClass } from "@hr/core/common/hr_employee_model";

    export interface HrEmployee extends HrEmployeeClass {}

    export interface Persona {
        employeeId: number|undefined;
    }
    export interface Store {
        "hr.employee": StaticMailRecord<HrEmployee, typeof HrEmployeeClass>;
        self_employee: HrEmployee;
    }

    export interface Models {
        "hr.employee": HrEmployee;
    }
}
