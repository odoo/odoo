import { ChatWindowPreview } from "@im_livechat/js/im_livechat_widget_preview/chat_window_preview";
import { LivechatButtonPreview } from "@im_livechat/js/im_livechat_widget_preview/livechat_button_preview";
import { Component, onWillDestroy, useOnChange, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

let nextId = 0;

export class ImLivechatWidgetPreview extends Component {
    static template = "im_livechat.ImLivechatWidgetPreview";
    static components = { ChatWindowPreview, LivechatButtonPreview };
    props = useProps(standardWidgetProps);

    setup() {
        this.store = useService("mail.store");
        const id = --nextId;
        this.channel = this.store["discuss.channel"].insert({
            id,
            channel_type: "livechat",
            channel_member_ids: [
                {
                    id,
                    partner_id: this.store.odoobot,
                    livechat_member_type: "agent",
                },
            ],
        });
        this.channel.thread.isLoaded = true;
        this.message = this.store["mail.message"].insert({
            id,
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
            this.chatWindow.delete();
            this.channel.delete();
        });
    }
}

registry.category("view_widgets").add("im_livechat_widget_preview", {
    component: ImLivechatWidgetPreview,
});
