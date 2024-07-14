/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

class WorksheetValidationController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async saveButtonClicked(params = {}) {
        // closable is a param that is set by default on form saves and will trigger a close window action if true
        // its set to false here to prevent the action close from closing the action in `onRecordSaved`
        params.closable = false;
        return super.saveButtonClicked(params);
    }

    async onRecordSaved(record) {
        if (record.mode != "readonly") {
            record.context['from_worksheet'] = true
            const action = await this.orm.call(
                "quality.check",
                "action_worksheet_check",
                [record.data.x_quality_check_id[0]],
                { context: record.context }
            );
            if (action) {
                await this.model.action.doAction(action);
            }
        }
    }

    async discard() {
        await super.discard();
        const record = this.model.root.data;
        const context = this.model.root.context;
        const action = await this.orm.call(
            "quality.check",
            "action_worksheet_discard",
            [record.x_quality_check_id[0]],
            { context }
        );
        this.action.doAction(action);
    }
}

export const WorksheetValidationFormView = {
    ...formView,
    Controller: WorksheetValidationController,
};

registry.category("views").add("worksheet_validation", WorksheetValidationFormView);
