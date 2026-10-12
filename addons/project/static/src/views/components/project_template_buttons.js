import { Component, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog, deleteConfirmationMessage } from "@web/core/confirmation_dialog/confirmation_dialog";

export class ProjectTemplateButtons extends Component {
    static template = "project.ProjectTemplateButtons";
    props = useProps({
        resModel: t.string(),
        resId: t.number(),
    });

    setup() {
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.action = useService("action");
    }

    onEditClick() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: this.props.resModel,
            res_id: this.props.resId,
            views: [[false, "form"]],
        });
    }

    async onDeleteClick() {
        this.dialogService.add(ConfirmationDialog, {
            body: deleteConfirmationMessage,
            confirm: async () => {
                await this.orm.unlink(this.props.resModel, [this.props.resId]);
                this.action.doAction("soft_reload");
            },
            cancel: () => {},
        });
    }
}
