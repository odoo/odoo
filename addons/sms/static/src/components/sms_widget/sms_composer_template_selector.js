/** @odoo-module **/

import { MailComposerTemplateSelector } from "@mail/core/web/mail_composer_template_selector";
import { patch } from "@web/core/utils/patch";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

patch(MailComposerTemplateSelector.prototype, {
    async fetchTemplates() {
        if (this.props.record.resModel === 'sms.composer') {
            const fields = ["display_name"];
            const domain = [["model", "=", this.props.record.data.res_model]];
            
            const templates = await this.orm.searchRead("sms.template", domain, fields, { limit: this.limit });
            this.state.templates = templates;
        } else {
            return super.fetchTemplates(...arguments);
        }
    },

    onSelectTemplateSearchMoreBtnClick() {
        if (this.props.record.resModel === 'sms.composer') {
            this.env.services.dialog.add(SelectCreateDialog, {
                resModel: "sms.template",
                title: this.env._t("Select a Template"),
                multiSelect: false,
                noCreate: true,
                domain: [["model", "=", this.props.record.data.res_model]],
                onSelected: async templateIds => {
                    await this.props.record.update({
                        template_id: { id: templateIds[0] },
                    });
                },
            });
        } else {
            return super.onSelectTemplateSearchMoreBtnClick(...arguments);
        }
    },

    async onManageTemplateBtnClick() {
        if (this.props.record.resModel === 'sms.composer') {
            const action = await this.action.loadAction("sms.sms_template_action");
            action.context = {
                search_default_model: this.props.record.data.model,
                default_model: this.props.record.data.model,
            };
            return this.action.doAction(action);
        } else {
            return super.onManageTemplateBtnClick(...arguments);
        }
    }
});
