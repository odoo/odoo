/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { SignTemplateControlPanel } from "./sign_template_control_panel";
import { SignTemplateBody } from "./sign_template_body";
import { Component, onWillStart } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class SignTemplate extends Component {
    static template = "sign.Template";
    static components = {
        SignTemplateControlPanel,
        SignTemplateBody,
    };
    static props = {
        ...standardActionServiceProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        const params = this.props.action.params;
        this.templateID = params.id;
        const name = this.props.action.name || params.name;

        if (this.templateID) {
            this.props.updateActionState({ id: this.templateID });
        }
        if (name) {
            this.env.config.setDisplayName(name);
            this.props.updateActionState({ name: name });
        }
        this.actionType = params.sign_edit_call || "";
        this.resModel = params.resModel || "";
        onWillStart(async () => {
            if (!this.templateID) {
                return this.goBackToKanban();
            }
            return Promise.all([this.checkManageTemplateAccess(), this.fetchTemplateData()]);
        });
    }

    _getTemplateFields() {
        return [
            "id",
            "attachment_id",
            "has_sign_requests",
            "responsible_count",
            "display_name",
            "active",
        ];
    }

    async fetchTemplateData() {
        const template = await this.orm.call("sign.template", "read", [
            [this.templateID],
            this._getTemplateFields(),
        ]);
        if (!template.length) {
            this.templateID = undefined;
            this.notification.add(_t("The template doesn't exist anymore."), {
                title: _t("Warning"),
                type: "warning",
            });
            return;
        }
        this.signTemplate = template[0];
        this.hasSignRequests = this.signTemplate.has_sign_requests;
        this.responsibleCount = this.signTemplate.responsible_count;
        this.attachmentLocation = `/web/content/${this.signTemplate.attachment_id[0]}`;

        return Promise.all([
            this.fetchSignItemData(),
            this.fetchAttachment(),
            this.fetchSignItemTypes(),
            this.fetchSignRoles(),
            this.fetchRadioSets(),
        ]);
    }

    async fetchRadioSets() {
        this.radioSets = await this.orm.call(
            "sign.template",
            "get_radio_sets_dict", [
                this.signTemplate.id
            ]
        );
    }

    async fetchSignItemTypes() {
        this.signItemTypes = await this.orm.call("sign.item.type", "search_read", [], {
            context: user.context,
        });
    }

    async fetchSignRoles() {
        this.signRoles = await this.orm.call("sign.item.role", "search_read", [], {
            context: user.context,
        });
    }

    async fetchSignItemData() {
        this.signItems = await this.orm.call(
            "sign.item",
            "search_read",
            [[["template_id", "=", this.signTemplate.id]]],
            { context: user.context }
        );

        // The ORM would format radio_set_id like: [49, 'sign.item.radio.set,49']
        // The format isn't important, we care only about the id.
        this.signItems.forEach((item) => {
            item.radio_set_id = item?.radio_set_id[0] || undefined;
        });

        this.signItemOptions = await this.orm.call(
            "sign.item.option",
            "search_read",
            [[], ["id", "value"]],
            { context: user.context }
        );
    }

    async fetchAttachment() {
        const attachment = await this.orm.call(
            "ir.attachment",
            "read",
            [[this.signTemplate.attachment_id[0]], ["mimetype", "name"]],
            { context: user.context }
        );

        this.signTemplateAttachment = attachment[0];
        this.isPDF = this.signTemplateAttachment.mimetype.indexOf("pdf") > -1;
    }

    /**
     * Checks that user has group sign.manage_template_access for showing extra fields
     */
    async checkManageTemplateAccess() {
        this.manageTemplateAccess = await user.hasGroup("sign.manage_template_access");
    }

    goBackToKanban() {
        return this.action.doAction("sign.sign_template_action", { clearBreadcrumbs: true });
    }
}

registry.category("actions").add("sign.Template", SignTemplate);
