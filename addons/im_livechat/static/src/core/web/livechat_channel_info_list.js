import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component } from "@odoo/owl";

import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { htmlEscape } from "@web/core/utils/html";

export class LivechatChannelInfoList extends Component {
    static components = { ActionPanel };
    static template = "im_livechat.channelInfoList";
    static props = ["thread"];

    setup() {
        super.setup();
        this.rpc = useService("orm");
    }

    onBlurNote() {
        rpc("/im_livechat/session/update_note", {
            channel_id: this.props.thread.id,
            note: htmlEscape(this.props.thread.livechatNoteText),
        });
    }
}
