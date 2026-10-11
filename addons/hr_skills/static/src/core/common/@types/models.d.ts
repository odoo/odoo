declare module "models" {
    import { HrEmployee as HrEmployeeClass } from "@hr/core/common/hr_employee_model";
    import { HrEmployeePublic as HrEmployeePublicClass } from "@hr/core/common/hr_employee_public_model";

    export interface HrEmployee extends Patch<HrEmployeeClass, typeof import("@hr_skills/core/common/hr_employee_model_patch").hrEmployeePatch> {}
    export interface HrEmployeePublic extends Patch<HrEmployeePublicClass, typeof import("@hr_skills/core/common/hr_employee_public_model_patch").hrEmployeePublicPatch> {}
}
