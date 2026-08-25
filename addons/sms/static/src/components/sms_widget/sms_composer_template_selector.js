/** @odoo-module **/

import { mailComposerTemplateSelector, MailComposerTemplateSelector } from "@mail/core/web/mail_composer_template_selector";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

if (mailComposerTemplateSelector.fieldDependencies) {
    mailComposerTemplateSelector.fieldDependencies = mailComposerTemplateSelector.fieldDependencies.filter(
        (dep) => dep.name !== "can_edit_body" && dep.name !== "render_model"
    );
}

patch(MailComposerTemplateSelector.prototype, {
    async fetchTemplates() {
        if (this.props.record.resModel === "sms.composer") {
            const fields = ["display_name"];
            const domain = [["model", "=", this.props.record.data.res_model]];

            const templates = await this.orm.searchRead("sms.template", domain, fields, { limit: this.limit });
            this.state.templates = templates;
            return;
        }
        return super.fetchTemplates(...arguments);
    },

    onSelectTemplateSearchMoreBtnClick() {
        if (this.props.record.resModel === "sms.composer") {
            this.env.services.dialog.add(SelectCreateDialog, {
                resModel: "sms.template",
                title: _t("Select a Template"),
                multiSelect: false,
                noCreate: true,
                domain: [["model", "=", this.props.record.data.res_model]],
                onSelected: async (templateIds) => {
                    await this.props.record.update({
                        template_id: templateIds[0],
                    });
                },
            });
            return;
        }
        return super.onSelectTemplateSearchMoreBtnClick(...arguments);
    },

    async onManageTemplateBtnClick() {
        if (this.props.record.resModel === "sms.composer") {
            const action = await this.action.loadAction("sms.sms_template_action");
            action.context = {
                search_default_model: this.props.record.data.res_model,
                default_model: this.props.record.data.res_model,
            };
            return this.action.doAction(action);
        }
        return super.onManageTemplateBtnClick(...arguments);
    },
});
