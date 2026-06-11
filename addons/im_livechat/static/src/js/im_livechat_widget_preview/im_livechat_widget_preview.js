import { ChatWindow } from "@mail/core/common/chat_window";

import { Component, onWillDestroy, useOnChange } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class ImLivechatWidgetPreview extends Component {
    static template = "im_livechat.ImLivechatWidgetPreview";
    static props = { ...standardWidgetProps };
    static components = { ChatWindow };

    setup() {
        this.store = useService("mail.store");
        this.channel = this.store["discuss.channel"].insert({
            id: -1,
            channel_type: "livechat",
            name: _t("Agent"),
        });
        this.channel.thread.isLoaded = true;
        this.message = this.store["mail.message"].insert({
            id: -1,
            author_id: this.store.odoobot,
            body: this.props.record.data.default_message,
            thread: this.channel.thread,
        });
        this.channel.thread.messages.push(this.message);
        this.chatWindow = this.store.ChatWindow.insert({ channel: this.channel });
        useOnChange(
            () => [this.props.record.data.default_message],
            (body) => (this.message.body = body)
        );
        onWillDestroy(() => {
            this.message.delete();
            this.channel.delete();
        });
    }
}

registry.category("view_widgets").add("im_livechat_widget_preview", {
    component: ImLivechatWidgetPreview,
});
