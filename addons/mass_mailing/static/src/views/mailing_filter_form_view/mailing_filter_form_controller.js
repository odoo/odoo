import { FormController } from "@web/views/form/form_controller";

export class MailingFilterFormController extends FormController {
    /**
     * Call `saveButtonClicked` with param `isSaveForLater: true` added
     * to the original params.
     *
     * Context: when opening the dynamic list (mailing.filter) form
     * dialog when saving a domain using the domain widget, in the
     * context of a mailing, the button `save for later` should have
     * different behavior from the normal save button.
     */
    saveForLaterButtonClicked(params = {}) {
        return this.saveButtonClicked({ ...params, isSaveForLater: true });
    }
}
