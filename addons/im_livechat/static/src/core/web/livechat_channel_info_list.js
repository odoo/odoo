import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { prettifyMessageContent } from "@mail/utils/common/format";

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

import { rpc } from "@web/core/network/rpc";

export class LivechatChannelInfoList extends Component {
    static components = { ActionPanel };
    static template = "im_livechat.channelInfoList";
    static props = ["thread"];

    setup() {
        super.setup();
    }

    get statusButtons() {
        return [
            {
                label: _t("In progress"),
                status: "in_progress",
                icon: "fa fa-circle-o",
            },
            {
                label: _t("Waiting for customer"),
                status: "waiting",
                icon: "fa fa-check",
            },
            {
                label: _t("Looking for help"),
                status: "need_help",
                icon: "fa fa-times",
            },
        ];
    }

    onBlurNote() {
        prettifyMessageContent(this.props.thread.livechatNoteText).then((note) => {
            rpc("/im_livechat/session/update_note", { channel_id: this.props.thread.id, note });
        });
    }

    updateLivechatStatus(livechat_status) {
        if (this.props.thread.livechat_status === livechat_status) {
            return;
        }
        rpc("/im_livechat/session/update_status", {
            channel_id: this.props.thread.id,
            livechat_status,
        });
    }
}
