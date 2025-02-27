import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MailComposerChatGPT extends Component {
    static template = "mail.MailComposerChatGPT";
    static props = { ...standardFieldProps };

    setup() {
        this.btnLabel = _t("AI"); // workaround to translate short string
        this.store = useService("mail.store");
        this.orm = useService("orm");
    }

    async onOpenChatGPTPromptDialogBtnClick() {
        // create the discuss channel used for talking with the ai
        const ai_channel_id = await this.orm.call(
            'discuss.channel',
            'create_ai_composer_channel',
            [ 
                this.props.record.data.record_name,
                this.props.record.data.model,
                this.props.record.data.res_ids,
            ], 
        );
        // create and open the thread for the discuss channel
        const thread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: Number(ai_channel_id), 
        });
        thread.open({ focus: true });
        // drop the mail composer dialog's z-index so the chat windows and bubble are above it
        const mail_composer_dialog = document.querySelector(".o-overlay-item");
        mail_composer_dialog.style.zIndex = "9"; 
        return;
    }
}

export const mailComposerChatGPT = {
    component: MailComposerChatGPT,
    fieldDependencies: [{ name: "body", type: "text" }],
};

registry.category("fields").add("mail_composer_chatgpt", mailComposerChatGPT);
