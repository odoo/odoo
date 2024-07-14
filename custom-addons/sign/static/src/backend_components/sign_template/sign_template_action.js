/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
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
        this.user = useService("user");
        this.action = useService("action");
        const params = this.props.action.params;
        this.templateID = params.id;
        this.actionType = params.sign_edit_call || "";
        onWillStart(async () => {
            if (!this.templateID) {
                return this.goBackToKanban();
            }
            return Promise.all([this.checkManageTemplateAccess(), this.fetchTemplateData()]);
        });
    }

    async fetchTemplateData() {
        const template = await this.orm.call("sign.template", "read", [
            [this.templateID],
            ["id", "attachment_id", "has_sign_requests", "responsible_count", "display_name"],
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
        ]);
    }

    async fetchSignItemTypes() {
        this.signItemTypes = await this.orm.call("sign.item.type", "search_read", [], {
            context: this.user.context,
        });
    }

    async fetchSignRoles() {
        this.signRoles = await this.orm.call("sign.item.role", "search_read", [], {
            context: this.user.context,
        });
    }

    async fetchSignItemData() {
        this.signItems = await this.orm.call(
            "sign.item",
            "search_read",
            [[["template_id", "=", this.signTemplate.id]]],
            { context: this.user.context }
        );

        this.signItemOptions = await this.orm.call(
            "sign.item.option",
            "search_read",
            [[], ["id", "value"]],
            { context: this.user.context }
        );
    }

    async fetchAttachment() {
        const attachment = await this.orm.call(
            "ir.attachment",
            "read",
            [[this.signTemplate.attachment_id[0]], ["mimetype", "name"]],
            { context: this.user.context }
        );

        this.signTemplateAttachment = attachment[0];
        this.isPDF = this.signTemplateAttachment.mimetype.indexOf("pdf") > -1;
    }

    /**
     * Checks that user has group sign.manage_template_access for showing extra fields
     */
    async checkManageTemplateAccess() {
        this.manageTemplateAccess = await this.user.hasGroup("sign.manage_template_access");
    }

    goBackToKanban() {
        return this.action.doAction("sign.sign_template_action", { clearBreadcrumbs: true });
    }
}

registry.category("actions").add("sign.Template", SignTemplate);
