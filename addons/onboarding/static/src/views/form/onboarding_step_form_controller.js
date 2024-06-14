/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";

/**
 * Controller to use for an onboarding step dialog, not the
 * onboarding.onboarding.step form view itself.
 */
export default class OnboardingStepFormController extends FormController {
    setup() {
        super.setup();
        this.action = useService('action');
        this.orm = useService('orm');
    }
    /**
     * If necessary, mark the step as done and reload the main view.
     * @override
     */
    async save({ closable, ...otherParams }) {
        const saved = await super.save(otherParams);
        if (saved) {
            let shouldClose = closable;
            if (await this.isStepCompleted()) {
                const { reloadOnFirstValidation, reloadAlways } = this.stepConfig;
                const validationResponse = await this.orm.call(
                    'onboarding.onboarding.step',
                    'action_validate_step',
                    [this.stepName],
                );
                if (reloadAlways || (reloadOnFirstValidation && validationResponse === "JUST_DONE")) {
                    shouldClose = false;
                    this.action.restore(this.action.currentController.jsId);
                } 
            }
            if (shouldClose) {
                this.action.doAction({ type: "ir.actions.act_window_close" });
            }
        }
        return saved;
    }
    /**
     * Returns the name of the onboarding step to validate after the dialog
     * record is saved
     *
     * @return {string}
     */
    get stepName() {
        return ''
    }
    /**
     *  Returns whether to reload the page (useful if the current
     * view needs to be updated).
     *
     * @returns {{reloadAlways: boolean, reloadOnFirstValidation: boolean}}
     */
    get stepConfig() {
        return { reloadAlways: false, reloadOnFirstValidation: false };
    }
    /**
     * Returns whether the step condition is met or not after
     * record is saved
     *
     * @return {boolean}
     */
    async isStepCompleted() {
        return true;
    }
}
