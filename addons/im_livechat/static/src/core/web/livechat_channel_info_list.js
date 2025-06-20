import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { prettifyMessageContent } from "@mail/utils/common/format";

import { Component } from "@odoo/owl";

import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class LivechatChannelInfoList extends Component {
    static components = { ActionPanel };
    static template = "im_livechat.channelInfoList";
    static props = ["thread"];

    setup() {
        super.setup();
        this.rpc = useService("orm");
    }

    onBlurNote() {
        prettifyMessageContent(this.props.thread.livechatNoteText).then((note) => {
            rpc("/im_livechat/session/update_note", { channel_id: this.props.thread.id, note });
        });
    }
}
