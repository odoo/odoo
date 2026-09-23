import { Component, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog, deleteConfirmationMessage } from "@web/core/confirmation_dialog/confirmation_dialog";

// For any Dropdown whose items embed ProjectTemplateButtons.
export const templateButtonsNavigationOptions = {
    // false: the default would target each row's first nested <button> (the edit
    // icon), so Enter would open the template instead of using it.
    shouldFocusChildInput: false,
    hotkeys: {
        // Rebound because the rows are <span>, not <button>.
        space: (navigator) => navigator.activeItem?.select(),
    },
};

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
