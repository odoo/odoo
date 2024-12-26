import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

import { Component, useState, onWillStart } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
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
        this.state = useState({});
        this.limit = 7;

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
                ["user_id", "!=", user.userId]
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
            template_id: [template.id]
        });
    }

    /**
     * @param {Object} template
     * @param {integer} template.id
     * @param {string} template.display_name
     */
    async onDeleteTemplate(template) {
        this.env.services.dialog.add(ConfirmationDialog, {
            body: sprintf(_t('Are you sure you want to delete "%(template_name)s"?'), {
                template_name: template.display_name,
            }),
            confirmLabel: _t("Delete Template"),
            confirm: async () => {
                await this.orm.unlink("mail.template", [template.id]);
                this.state.templates = this.state.templates.filter(current => {
                    return current.id !== template.id;
                });
            },
            cancel: () => {},
        });
    }

    /**
     * @param {Object} template
     * @param {integer} template.id
     * @param {string} template.display_name
     */
    async onOverwriteTemplate(template) {
        this.env.services.dialog.add(ConfirmationDialog, {
            body: sprintf(_t('Are your sure you want to update "%(template_name)s"?'), {
                template_name: template.display_name,
            }),
            confirmLabel: _t("Update Template"),
            confirm: async () => {
                await this.orm.write("mail.template", [template.id], {
                    subject: this.props.record.data.subject,
                    body_html: this.props.record.data.body,
                });
            },
            cancel: () => {},
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

    onSelectTemplateSearchMoreBtnClick() {
        this.env.services.dialog.add(SelectCreateDialog, {
            resModel: "mail.template",
            title: _t("Insert Templates"),
            multiSelect: false,
            noCreate: true,
            domain: [["model", "=", this.props.record.data.render_model]],
            onSelected: async templateIds => {
                await this.props.record.update({
                    template_id: templateIds
                });
            },
        });
    }

    onDeleteTemplateSearchMoreBtnClick() {
        this.env.services.dialog.add(SelectCreateDialog, {
            resModel: "mail.template",
            title: _t("Delete Template"),
            multiSelect: true,
            noCreate: true,
            domain: [["model", "=", this.props.record.data.render_model]],
            onSelected: async templateIds => {
                await this.orm.unlink("mail.template", templateIds);
                this.state.templates = this.state.templates.filter(current => {
                    return !templateIds.includes(current.id);
                });
            },
        });
    }

    onOverwriteTemplateSearchMoreBtnClick() {
        this.env.services.dialog.add(SelectCreateDialog, {
            resModel: "mail.template",
            title: _t("Overwrite Template"),
            multiSelect: false,
            noCreate: true,
            domain: [["model", "=", this.props.record.data.render_model]],
            onSelected: async templateIds => {
                await this.orm.write("mail.template", templateIds, {
                    subject: this.props.record.data.subject,
                    body_html: this.props.record.data.body,
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
