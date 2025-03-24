import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { prettifyMessageContent } from "@mail/utils/common/format";

import { Component } from "@odoo/owl";

import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { startUrl } from "@web/core/browser/router";

export class LivechatChannelInfoList extends Component {
    static components = { ActionPanel };
    static template = "im_livechat.LivechatChannelInfoList";
    static props = ["thread"];

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
    }

    onBlurNote() {
        prettifyMessageContent(this.props.thread.livechatNoteText).then((note) => {
            rpc("/im_livechat/session/update_note", { channel_id: this.props.thread.id, note });
        });
    }

    openVisitorProfile() {
        if (this.ui.isSmall) {
            this.store.ChatWindow.get({ thread: this.props.thread })?.fold();
        } else {
            this.props.thread.openChatWindow({ focus: true });
        }
    }

    get visitorProfileURL() {
        const visitorPersona = this.props.thread?.livechatVisitorMember?.persona;
        if (visitorPersona?.type === "partner") {
            return url(`/${startUrl()}/res.partner/${visitorPersona.id}`);
        }
        return null;
    }
}
