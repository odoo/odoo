declare module "models" {
    import { HrApplicant as HrApplicantClass } from "@hr_recruitment/core/common/hr_applicant_model";

    export interface HrApplicant extends HrApplicantClass {}

    export interface ResPartner {
        applicant_ids: HrApplicant[];
    }
    export interface Store {
        "hr.applicant": StaticMailRecord<HrApplicant, typeof HrApplicantClass>;
    }

    export interface Models {
        "hr.applicant": HrApplicant;
    }
}
