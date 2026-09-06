import { Component, usePlugin } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { ORM } from "@web/core/orm_plugin";

const cogMenuRegistry = registry.category("cogMenu");

export class MassMailingSaveAsTemplateCogMenu extends Component {
    static template = "mass_mailing.MassMailingSaveAsTemplateCogMenu";
    static components = { DropdownItem };

    setup() {
        this.notification = usePlugin(NotificationPlugin);
        this.orm = usePlugin(ORM);
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.dropdown = useDropdownCloser();
        this.label = _t("Save as Template");
    }

    saveConfirmationDialogProps() {
        const subject = this.env.model.root.data.subject;
        const modelName = this.env.model.root.data.mailing_model_id?.display_name;
        const body = _t(
            `A similar template with subject %(subject)s and model %(modelName)s already exists.\n\nDo you want to proceed ?`,
            { subject: subject, modelName: modelName }
        );
        return {
            title: _t("Similar template found!"),
            body,
            confirm: async () => {
                await this.createTemplate();
                this.dropdown.closeAll();
            },
            confirmLabel: _t("Save"),
            confirmClass: "btn-primary",
            cancel: () => this.dropdown.closeAll(),
            cancelLabel: _t("Do not save"),
        };
    }

    async createTemplate() {
        await this.orm.call("mailing.mailing", "action_save_as_template", [
            [this.env.model.root.resId],
        ]);
        this.notification.add(_t("Design added to your Template Library!"), {
            type: "success",
        });
    }

    async isSimilarTemplateExists(data) {
        const count = await this.orm.searchCount("mailing.mailing", [
            ["mailing_model_id", "=", data.modelId],
            ["id", "!=", data.id],
            ["is_template", "=", true],
            ["subject", "=", data.subject],
        ]);
        return count > 0;
    }

    async saveAsTemplate() {
        const res = await this.env.model.root.save();
        if (!res) {
            return;
        }
        const data = this.env.model.root.data;
        const exists = await this.isSimilarTemplateExists({
            modelId: data.mailing_model_id?.id,
            id: this.env.model.root.resId,
            subject: data.subject,
        });
        if (exists) {
            this.dialog.add(ConfirmationDialog, this.saveConfirmationDialogProps());
        } else {
            await this.createTemplate();
            this.dropdown.closeAll();
        }
    }
}

export const MassMailingSaveAsTemplateCogMenuItem = {
    Component: MassMailingSaveAsTemplateCogMenu,
    groupNumber: 4,
    isDisplayed: async (env) =>
        env.searchModel.resModel === "mailing.mailing" &&
        env.model.root.data?.mailing_type === "mail" &&
        !env.model.root.data?.is_template &&
        env.config.viewType == "form" &&
        env.config.actionType === "ir.actions.act_window",
};

cogMenuRegistry.add("save-as-template-menu", MassMailingSaveAsTemplateCogMenuItem, {
    sequence: 10,
});
