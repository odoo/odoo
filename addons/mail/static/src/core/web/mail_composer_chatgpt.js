import { ChatGPTPromptDialog } from "@html_editor/main/chatgpt/chatgpt_prompt_dialog";

import { htmlJoin } from "@mail/utils/common/html";

import { Component, markup } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MailComposerChatGPT extends Component {
    static template = "mail.MailComposerChatGPT";
    static props = { ...standardFieldProps };

    setup() {
        this.btnLabel = _t("AI"); // workaround to translate short string
    }

    async onOpenChatGPTPromptDialogBtnClick() {
        this.env.services.dialog.add(ChatGPTPromptDialog, {
            /** @param {DocumentFragment} content */
            insert: (content) => {
                const root = document.createElement("div");
                root.appendChild(content);
                const { body } = this.props.record.data;
                this.props.record.update({
                    body: htmlJoin(body, markup(root.innerHTML)),
                });
            },
            /**
             * @param {HTMLElement} fragment
             * @returns {string}
             */
            sanitize: (fragment) => {
                return DOMPurify.sanitize(fragment, {
                    IN_PLACE: true,
                    ADD_TAGS: ["#document-fragment"],
                    ADD_ATTR: ["contenteditable"],
                });
            },
        });
    }
}

export const mailComposerChatGPT = {
    component: MailComposerChatGPT,
    fieldDependencies: [{ name: "body", type: "text" }],
};

registry.category("fields").add("mail_composer_chatgpt", mailComposerChatGPT);
