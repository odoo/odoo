/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from '@web/core/registry';
import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';

export class EventTrackFormController extends FormController {
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "unlink") {
            const canProceed = await new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    body: _t("Are you sure you want to delete this track?"),
                    cancel: () => resolve(false),
                    close: () => resolve(false),
                    confirm: () => resolve(true),
                });
            });
            if (!canProceed) {
                return false;
            }
        }
        return super.beforeExecuteActionButton(clickParams);
    }
}

registry.category('views').add('event_track_form_in_gantt', {
    ...formView,
    Controller: EventTrackFormController,
});
