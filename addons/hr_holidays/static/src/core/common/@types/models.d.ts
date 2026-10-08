declare module "models" {
    import { HrEmployee as HrEmployeeClass } from "@hr/core/common/hr_employee_model";
    import { ResPartner as ResPartnerClass } from "@mail/core/common/res_partner_model";
    import { ResUsers as ResUsersClass } from "@mail/core/common/res_users_model";

    export interface HrEmployee extends Patch<HrEmployeeClass, typeof import("@hr_holidays/core/common/hr_employee_model_patch").hrEmployeePatch> {
        leave_date_to: import("luxon").DateTime;
    }
    export interface ResPartner extends Patch<ResPartnerClass, typeof import("@hr_holidays/core/common/res_partner_model_patch").resPartnerPatch> {}
    export interface ResUsers extends Patch<ResUsersClass, typeof import("@hr_holidays/core/common/res_users_model_patch").resUsersPatch> {}
}
