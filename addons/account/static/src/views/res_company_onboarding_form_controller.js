/** @odoo-module **/

import OnboardingStepFormController from "@onboarding/views/form/onboarding_step_form_controller";

/**
 * Validate the onboarding step on saving a record of another model (here `res.company`).
 **/
export default class CompanyOnboardingFormController extends OnboardingStepFormController {
    get stepName() {
        return "account.onboarding_onboarding_step_company_data";
    }
}
