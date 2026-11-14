import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { MultiVersionUpdateConfirmationDialog } from "./form/multi_version_update_confirmation_dialog";

const CONTRACT_GENERATION_ACTIONS = ["action_generate_pdf", "action_send_pdf"];

export class HrContractPdfWizardFormController extends FormController {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
    }

    /**
     * Generating the contract saves the wizard values on the version: when the
     * employee has later versions, ask whether to update them too, as the
     * employee form does.
     *
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        const saved = await super.beforeExecuteActionButton(...arguments);
        if (saved === false || !CONTRACT_GENERATION_ACTIONS.includes(clickParams.name)) {
            return saved;
        }
        const versionChanges = await this.orm.call(
            "hr.contract.pdf.wizard",
            "get_future_version_changes",
            [this.model.root.resId]
        );
        if (!Object.keys(versionChanges).length) {
            return true;
        }
        return new Promise((resolve) => {
            this.dialogService.add(
                MultiVersionUpdateConfirmationDialog,
                {
                    title: _t("Apply changes to next versions?"),
                    version_changes: versionChanges,
                    cancel: () => resolve(false),
                    change_current: () => resolve(true),
                    change_multi: () => {
                        clickParams.buttonContext = {
                            ...clickParams.buttonContext,
                            hr_contract_update_future_versions: true,
                        };
                        resolve(true);
                    },
                },
                {
                    onClose: () => resolve(false),
                }
            );
        });
    }
}

registry.category("views").add("hr_contract_pdf_wizard_form", {
    ...formView,
    Controller: HrContractPdfWizardFormController,
});
