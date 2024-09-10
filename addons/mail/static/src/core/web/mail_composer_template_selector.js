import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
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
        this.state = useState({});
        this.limit = 7;

        onWillStart(() => {
            this.fetchTemplates();
        });
    }

    async fetchTemplates() {
        const domain = [["model", "=", this.props.record.data.render_model]];
        const fields = ["display_name"];
        this.state.templates = await this.orm.searchRead("mail.template", domain, fields, { limit: this.limit });
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

    async onSaveTemplate() {
        await this.props.record.save();
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
}

export const mailComposerTemplateSelector = {
    component: MailComposerTemplateSelector,
    fieldDependencies: [
        { name: "can_edit_body", type: "boolean" },
        { name: "render_model", type: "string" },
    ],
};

registry.category("fields").add("mail_composer_template_selector", mailComposerTemplateSelector);
