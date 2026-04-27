import { EvaluationError, helpers } from "@odoo/o-spreadsheet";
import { useSubEnv } from "@odoo/owl";

const { toBoolean } = helpers;

import { registry } from "@web/core/registry";
import { QualitySpreadsheetTemplateAction } from "../quality_spreadsheet_template_action/quality_spreadsheet_template_action";

export class QualityCheckSpreadsheetAction extends QualitySpreadsheetTemplateAction {
    static template = "quality_control_spreadsheet.QualityCheckSpreadsheetAction";
    static path = "quality-check-spreadsheet";

    resModel = "quality.check.spreadsheet";

    setup() {
        super.setup();
        this.qualityCheckWizardId = this.params.quality_check_wizard_id;
        this.qualityCheckId = this.params.check_id;
        this.props.updateActionState({ check_id: this.qualityCheckId })
        useSubEnv({
            makeCopy: false, // disable copy
        });
    }

    async writeToQualityCheck() {
        const method = this.isCheckPassed() ? this.params.pass_action ?? "do_pass" : this.params.fail_action ?? "do_fail"
        if (this.qualityCheckWizardId) {
            // we are part of the quality check wizard flow
            this.writeToQualityCheckWizard(method);
        } else {
            const action = await this.orm.call(
                "quality.check",
                method,
                [this.qualityCheckId],
                { context: this.props.action.context },
            );
            if (action && action.type === 'ir.actions.act_window') {
                return this.actionService.doAction(action);
            }
            await this.goBack();
        }
    }

    async writeToQualityCheckWizard(method) {
        const nextQualityCheckAction = await this.orm.call(
            "quality.check.wizard",
            method,
            [this.qualityCheckWizardId],
            { context: this.props.action.context },
        );
        if (nextQualityCheckAction.type === "ir.actions.act_window_close")  {
            await this.goBack();
        } else if (nextQualityCheckAction.target === "new") {
            await this.goBack();
            await this.actionService.doAction(nextQualityCheckAction);
        } else {
            const options = {
                stackPosition: "replaceCurrentAction",
            }
            this.actionService.doAction(nextQualityCheckAction, options);
        }
    }

    isCheckPassed() {
        const resultPosition = this.model.getters.getQualityCheckResultPosition();
        if (!resultPosition) {
            // there's no condition, let it pass
            return true;
        }
        const evaluatedCell = this.model.getters.getEvaluatedCell(resultPosition);
        try {
            return toBoolean(evaluatedCell.value);
        } catch (error) {
            if (error instanceof EvaluationError) {
                return false;
            }
            throw error;
        }
    }

    async goBack() {
        if (this.actionService.currentController.state.actionStack.length > 1) {
            await this.actionService.restore();
        }
    }

}

registry
    .category("actions")
    .add("action_spreadsheet_quality", QualityCheckSpreadsheetAction, { force: true });
