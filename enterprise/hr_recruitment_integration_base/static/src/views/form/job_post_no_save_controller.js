import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class JobPostNoSaveFormController extends FormController {

    static template = "hr_recruitment_integration_base.job_post_no_save_form_template";

    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
    }

    /**
     * @override
     */
    getStaticActionMenuItems() {
        const { activeActions } = this.archInfo;
        return {
            duplicate: {
                isAvailable: () => activeActions.edit,
                sequence: 30,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.duplicateRecord(),
            },
            delete: {
                isAvailable: () => activeActions.delete && !this.model.root.isNew,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                callback: () => this.deleteRecord(),
                skipSave: true,
            },
        };
    }


    /**
     * @override
     */
    async duplicateRecord() {
        const action = await this.orm.call(
            "hr.job.post",
            "action_post_job",
            [this.model.root.resId]
        );
        this.action.doAction(action);
    }
}
