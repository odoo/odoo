import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { htmlJoin } from "@mail/utils/common/html";

import { Component, markup, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { unwrapContents } from "@html_editor/utils/dom";

export class MailComposerChatGPT extends Component {
    static template = "mail.MailComposerChatGPT";
    static props = { ...standardFieldProps };

    setup() {
        this.btnLabel = _t("AI"); // workaround to translate short string
        this.store = useService("mail.store");
        this.orm = useService("orm");
        this.areWeInDiscuss = this.store.discuss.isActive
        onMounted(() => {
            this.store["mail.message"].insertButtonCaller = this.props.record.id
            this.store.discuss.isActive = false;
        });
        onWillUnmount(() => {
            this.store["mail.message"].insertButtonCaller = false
            this.store.discuss.isActive = this.areWeInDiscuss;
        });
    }

    async onOpenChatGPTPromptDialogBtnClick() {
        // create the discuss channel used for talking with the ai
        const ai_channel_id = await this.orm.call(
            'discuss.channel',
            'create_ai_composer_channel',
            [ 
                'composer_ai_button',
                this.props.record.data.record_name,
                this.props.record.data.model,
                Number(this.props.record.data.res_ids.slice(1,-1)),
            ], 
        );
        // create and open the thread for the discuss channel
        const thread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: Number(ai_channel_id), 
        });
        thread.open({ 
            focus: true, 
            specialActions: {
                'insert': (content) => {
                    const root = document.createElement("div");
                    root.appendChild(content);
                    const { body } = this.props.record.data;
                    this.props.record.update({
                        body: htmlJoin(markup(root.innerHTML), body),
                    });
                },
            },
            chatCaller: this.props.record.id,
            composerText: 'Write a follow up answer',
        });
        return;
    }
}

export const mailComposerChatGPT = {
    component: MailComposerChatGPT,
    fieldDependencies: [{ name: "body", type: "text" }],
};

registry.category("fields").add("mail_composer_chatgpt", mailComposerChatGPT);
