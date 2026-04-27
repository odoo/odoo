/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

class WorksheetValidationController extends FormController {
    static template = "quality_control_worksheet.WorksheetValidationController";

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async validate() {
        const context = this.model.root.context;
        await this.saveButtonClicked({ closable: !context['quality_wizard_id'] });
        const record = this.model.root.data;
        if (record.mode != "readonly" && context['quality_wizard_id']) {
            context['from_worksheet'] = true
            const action = await this.orm.call(
                "quality.check",
                "action_worksheet_check",
                [record.x_quality_check_id[0]],
                { context }
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
        this.model.action.doAction(action);
    }

    async next() {
        const context = this.model.root.context;
        const action = await this.orm.call(
            "quality.check.wizard",
            "action_generate_next_window",
            [context.quality_wizard_id],
            { context }
        );
        await this.saveButtonClicked({ closable:false });
        this.model.action.doAction(action);
    }

    async previous() {
        const context = this.model.root.context;
        const action = await this.orm.call(
            "quality.check.wizard",
            "action_generate_previous_window",
            [context.quality_wizard_id],
            { context }
        );
        await this.saveButtonClicked({ closable:false });
        this.model.action.doAction(action);
    }

    showNextButton() {
        const context = this.model.root.context;
        return context.quality_wizard_id && context.default_current_check_id !== context.default_check_ids[context.default_check_ids.length - 1];
    }

    showPreviousButton() {
        const context = this.model.root.context;
        return context.quality_wizard_id && context.default_current_check_id !== context.default_check_ids[0];
    }
}

export const WorksheetValidationFormView = {
    ...formView,
    Controller: WorksheetValidationController,
};

registry.category("views").add("worksheet_validation", WorksheetValidationFormView);
