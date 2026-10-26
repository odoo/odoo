declare module "models" {
    import { HrApplicant as HrApplicantClass } from "@hr_recruitment/core/common/hr_applicant_model";
    import { ResPartner as ResPartnerClass } from "@mail/core/common/res_partner_model";

    export interface HrApplicant extends HrApplicantClass {}

    export interface ResPartner extends Patch<ResPartnerClass, typeof import("@hr_recruitment/core/common/res_partner_model_patch").resPartnerPatch> {
        applicant_ids: HrApplicant[];
    }
    export interface Store {
        "hr.applicant": StaticMailRecord<HrApplicant, typeof HrApplicantClass>;
    }
    export interface Models {
        "hr.applicant": HrApplicant;
    }
}
