import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { ORM } from "@web/core/orm_plugin";
import { Record } from "@web/model/relational_model/record";
import { getFieldDomain } from "@web/model/relational_model/utils";

import { Component, onWillStart, proxy, types, usePlugin, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

export class MailComposerTemplateSelector extends Component {
    static template = "mail.MailComposerTemplateSelector";
    static components = { Dropdown, DropdownItem };

    setup() {
        this.props = useProps({
            domain: types.or([types.array(), types.function()]).optional(),
            name: types.string(),
            record: types.instanceOf(Record),
        });
        this.action = useService("action");
        this.orm = usePlugin(ORM);
        this.limit = 80;

        const { context } = this.props.record.evalContext;
        this.state = proxy({
            hideMailTemplateManagementOptions: context?.hide_mail_template_management_options,
            templates: [],
        });

        onWillStart(() => {
            this.fetchTemplates();
        });
    }

    /**
     * Saving the body as a template is allowed only when it can be edited, as
     * it otherwise comes from the current template.
     */
    get canSaveTemplate() {
        return this.props.record.data.can_edit_body;
    }

    get templateDomain() {
        return getFieldDomain(this.props.record, this.props.name, this.props.domain);
    }

    get templateModel() {
        return this.props.record.fields[this.props.name].relation;
    }

    async fetchTemplates() {
        this.state.templates = await this.orm.searchRead(
            this.templateModel,
            this.templateDomain,
            ["display_name"],
            { limit: this.limit }
        );
    }

    /**
     * @param {Object} template
     * @param {integer} template.id
     * @param {string} template.display_name
     */
    async onLoadTemplate(template) {
        await this.props.record.update({
            [this.props.name]: { id: template.id },
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
            resModel: this.props.record.resModel,
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
            resModel: this.templateModel,
            title: _t("Select a Template"),
            multiSelect: false,
            noCreate: true,
            domain: this.templateDomain,
            onSelected: async (templateIds) => {
                await this.onLoadTemplate({ id: templateIds[0] });
            },
        });
    }
}

export const mailComposerTemplateSelector = {
    component: MailComposerTemplateSelector,
    extractProps: (fieldInfo, dynamicInfo) => ({ domain: dynamicInfo.domain }),
    fieldDependencies: [{ name: "can_edit_body", type: "boolean" }],
};

registry.category("fields").add("mail_composer_template_selector", mailComposerTemplateSelector);
