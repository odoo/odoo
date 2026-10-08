declare module "models" {
    import { HrDepartment as HrDepartmentClass } from "@hr/core/common/hr_department_model";
    import { HrEmployee as HrEmployeeClass } from "@hr/core/common/hr_employee_model";
    import { HrEmployeePublic as HrEmployeePublicClass } from "@hr/core/common/hr_employee_public_model";
    import { HrEmployeeType as HrEmployeeTypeClass } from "@hr/core/common/hr_employee_type_model";
    import { HrWorkLocation as HrWorkLocationClass } from "@hr/core/common/hr_work_location_model";
    import { ResourceResource as ResourceResourceClass } from "@resource_mail/core/common/resource_resource_model";
    import { ResPartner as ResPartnerClass } from "@mail/core/common/res_partner_model";
    import { ResUsers as ResUsersClass } from "@mail/core/common/res_users_model";
    import { Store as StoreClass } from "@mail/core/common/store_plugin";

    export interface HrDepartment extends HrDepartmentClass {}
    export interface HrEmployee extends HrEmployeeClass {}
    export interface HrEmployeePublic extends HrEmployeePublicClass {}
    export interface HrEmployeeType extends HrEmployeeTypeClass {}
    export interface HrWorkLocation extends HrWorkLocationClass {}

    export interface ResPartner extends Patch<ResPartnerClass, typeof import("@hr/core/common/res_partner_model_patch").resPartnerPatch> {
        employee_id: HrEmployee;
        employee_ids: HrEmployee[];
        employeeId: number|undefined;
    }
    export interface ResUsers extends Patch<ResUsersClass, typeof import("@hr/core/common/res_users_model_patch").resUsersPatch> {
        all_employee_ids: HrEmployee[];
        employee_id: HrEmployee;
    }
    export interface ResourceResource extends Patch<ResourceResourceClass, typeof import("@hr/core/common/resource_resource_model_patch").resourceResourcePatch> {
        department_id: HrDepartment;
        employee_id: HrEmployee[];
    }
    export interface Store extends Patch<StoreClass, typeof import("@hr/core/common/store_service_patch").storeServicePatch> {
        "hr.department": StaticMailRecord<HrDepartment, typeof HrDepartmentClass>;
        "hr.employee": StaticMailRecord<HrEmployee, typeof HrEmployeeClass>;
        "hr.employee.public": StaticMailRecord<HrEmployeePublic, typeof HrEmployeePublicClass>;
        "hr.employee.type": StaticMailRecord<HrEmployeeType, typeof HrEmployeeTypeClass>;
        "hr.work.location": StaticMailRecord<HrWorkLocation, typeof HrWorkLocationClass>;
    }
    export interface Models {
        "hr.department": HrDepartment;
        "hr.employee": HrEmployee;
        "hr.employee.public": HrEmployeePublic;
        "hr.employee.type": HrEmployeeType;
        "hr.work.location": HrWorkLocation;
    }
}
