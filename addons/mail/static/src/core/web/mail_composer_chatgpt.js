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
        this.store = useService("mail.store");
        this.orm = useService("orm");
        onMounted(() => {
            this.store.aiInsertButtonTarget = this.props.record.id
        });
        onWillUnmount(() => {
            this.store.aiInsertButtonTarget = false
        });
    }

    async onOpenChatGPTPromptDialogBtnClick() {
        const ai_channel_id = await this.orm.call(
            'discuss.channel',
            'create_ai_composer_channel',
            [ 
                'composer_ai_button',
                this.props.record.data.record_name,
                this.props.record.data.model,
                Number(this.props.record.data.res_ids.slice(1,-1)),  // resIds should look like so `[id]`, the slice and cast allows to extact the id
            ], 
        );
        const thread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: Number(ai_channel_id), 
        });
        thread.composer.text = _t('Write a follow up answer');
        thread.aiSpecialActions = {
            'insert': (content) => {
                const root = document.createElement("div");
                root.appendChild(content);
                const { body } = this.props.record.data;
                this.props.record.update({
                    body: htmlJoin(markup(root.innerHTML), body),
                });
            },
        };
        thread.aiChatSource = this.props.record.id;
        thread.open({ 
            focus: true,
        });
        return;
    }
}

export const mailComposerChatGPT = {
    component: MailComposerChatGPT,
    fieldDependencies: [{ name: "body", type: "text" }],
};

registry.category("fields").add("mail_composer_chatgpt", mailComposerChatGPT);
