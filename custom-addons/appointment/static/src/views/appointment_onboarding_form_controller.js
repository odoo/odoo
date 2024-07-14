/** @odoo-module **/

import OnboardingStepFormController from "@onboarding/views/form/onboarding_step_form_controller";


export default class AppointmentOnboardingAppointmentTypeFormController extends OnboardingStepFormController {
    /**
     * @override
     */
    get stepName() {
        return "appointment.appointment_onboarding_create_appointment_type_step";
    }
    /**
     * Reload the view below the onboarding panel as records may have been
     * created/modified.
     */
    get stepConfig() {
        return { ...super.stepConfig, reloadAlways: true };
    }
}
