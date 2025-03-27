import { Thread } from "@mail/core/common/thread_model";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { assignDefined } from "@mail/utils/common/misc";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { url } from "@web/core/utils/urls";

patch(Thread.prototype, {
    generate(prompt, channel_id, callback) {
        // send the prompt to the model using an rpc call (as done in @html_editor/chatgpt/chatgpt_dialog.js)
        this.pendingRpcPromise = rpc(
            "/ai_apps/generate_w_composer",
            {
                prompt,
                channel_id,
            },
            { shadow: true }
        );
        return this.pendingRpcPromise
            .then((content) => console.log(content))
            .catch((error) => console.log(error));
    },
    submitPrompt(written_prompt, channel_id) {
        this.generate(written_prompt, channel_id, (content, isError) => {
            if (isError) {
                console.log("An error occured while generating a response :(");
            } else {
                console.log(content); 
            }
        });
    },
    async post() {
        const message = await super.post(...arguments);
        if (this.channel_type === "ai_composer") {
            this.submitPrompt(message.body, this.id);
        }
        return message;
    },
    async openChatWindow({focus = false, fromMessagingMenu, specialActions, composerText, chatCaller} = {}) {
        if (this.channel_type !== "ai_composer") {
            return super.openChatWindow(focus, fromMessagingMenu);
        }
        await this.store.chatHub.initPromise;
        const cw = this.store.ChatWindow.insert(
            assignDefined({ thread: this, specialActions, composerText, chatCaller }, { fromMessagingMenu })
        );
        cw.open({ focus: focus });
        if (isMobileOS()) {
            this.markAsRead();
        }
        return cw;
    },
    get avatarUrl() {
        if (this.channel_type === "ai_composer") {
            return url("/ai_apps/static/description/icon.png");
        }
        return super.avatarUrl;
    }
});
