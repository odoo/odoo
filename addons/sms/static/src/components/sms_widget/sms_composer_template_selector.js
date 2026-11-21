import {
    mailComposerTemplateSelector,
    MailComposerTemplateSelector,
} from "@mail/core/web/mail_composer_template_selector";
import { registry } from "@web/core/registry";

export class SmsComposerTemplateSelector extends MailComposerTemplateSelector {
    get canSaveTemplate() {
        return true;
    }

    async onManageTemplateBtnClick() {
        const action = await this.action.loadAction("sms.sms_template_action");
        action.context = {
            search_default_model: this.props.record.data.res_model,
            default_model: this.props.record.data.res_model,
        };
        this.action.doAction(action);
    }
}

registry.category("fields").add("sms_composer_template_selector", {
    ...mailComposerTemplateSelector,
    component: SmsComposerTemplateSelector,
    fieldDependencies: [],
});
