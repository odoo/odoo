/** @odoo-module **/
import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import OnboardingStepFormController from "@onboarding/views/form/onboarding_step_form_controller";


export default class SetupBankManualConfigFormController extends OnboardingStepFormController {
    /**
     * @override
     */
    get stepName() {
        return "account.onboarding_onboarding_step_bank_account";
    }
    /**
     * Reload the view to show the newly created bank account
     */
    get stepConfig() {
        return { ...super.stepConfig, reloadAlways: true };
    }
}

const SetupBankManualConfigFormView = {
    ...formView,
    Controller: SetupBankManualConfigFormController,
};

registry.category("views").add('setup_bank_manual_config_form', SetupBankManualConfigFormView);
