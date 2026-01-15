import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

import { Component, useState, onWillStart } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";


export class MailComposerTemplateSelector extends Component {
    static template = "mail.MailComposerTemplateSelector";
    static components = { Dropdown, DropdownItem };
    static props = { ...standardFieldProps };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.limit = 80;

        const { context } = this.props.record.evalContext;
        this.state = useState({
            hideMailTemplateManagementOptions: context?.hide_mail_template_management_options,
        });

        onWillStart(() => {
            this.fetchTemplates();
        });
    }

    async fetchTemplates() {
        const fields = ["display_name"];
        const templates = await this.orm.searchRead("mail.template", [
            ["model", "=", this.props.record.data.render_model],
            ["user_id", "=", user.userId]
        ], fields, { limit: this.limit });
        if (templates.length < this.limit) {
            templates.push(...await this.orm.searchRead("mail.template", [
                ["model", "=", this.props.record.data.render_model],
                ["user_id", "=", false]
            ], fields, { limit: this.limit - templates.length }));
        }
        this.state.templates = templates;
    }

    /**
     * @param {Object} template
     * @param {integer} template.id
     * @param {string} template.display_name
     */
    async onLoadTemplate(template) {
        await this.props.record.update({
            template_id: { id: template.id },
        });
    }

    async onSaveTemplate() {
        if (!(await this.props.record.save())) {
            return;
        }
        await this.action.doActionButton({
            type: "object",
            name: "open_template_creation_wizard",
            resId: this.props.record.resId,
            resModel: this.props.record.resModel
        });
    }

    async onManageTemplateBtnClick() {
        const action = await this.action.loadAction("mail.action_email_template_tree_all");
        action.context = {
            search_default_my_templates: 1,
            search_default_model: this.props.record.data.model,
            default_model: this.props.record.data.model,
            default_user_id: user.userId,
        };
        this.action.doAction(action);
    }

    onSelectTemplateSearchMoreBtnClick() {
        this.env.services.dialog.add(SelectCreateDialog, {
            resModel: "mail.template",
            title: _t("Select a Template"),
            multiSelect: false,
            noCreate: true,
            domain: [["model", "=", this.props.record.data.render_model]],
            onSelected: async templateIds => {
                await this.props.record.update({
                    template_id: { id: templateIds[0] },
                });
            },
        });
    }
}

export const mailComposerTemplateSelector = {
    component: MailComposerTemplateSelector,
    fieldDependencies: [
        { name: "can_edit_body", type: "boolean" },
        { name: "render_model", type: "string" },
    ],
};

registry.category("fields").add("mail_composer_template_selector", mailComposerTemplateSelector);
