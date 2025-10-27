import { TranscriptSender } from "@im_livechat/core/common/transcript_sender";

import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { prettifyMessageContent } from "@mail/utils/common/format";

import { Component, useEffect, useSubEnv } from "@odoo/owl";

import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { startUrl } from "@web/core/browser/router";
import { BadgeTag } from "@web/core/tags_list/badge_tag";

export class LivechatChannelInfoList extends Component {
    static components = { ActionPanel, BadgeTag, TranscriptSender };
    static template = "im_livechat.LivechatChannelInfoList";
    static props = ["thread"];

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        useSubEnv({ inLivechatInfoPanel: true });
        useEffect(
            () => {
                if (this.props.thread.hasFetchedLivechatSessionData) {
                    return;
                }
                this.store.fetchStoreData("/im_livechat/session/data", {
                    channel_id: this.props.thread.id,
                });
                this.props.thread.hasFetchedLivechatSessionData = true;
            },
            () => [this.props.thread.id, this.props.thread.hasFetchedLivechatSessionData]
        );
    }

    get expectAnswerSteps() {
        return this.props.thread.messages
            .filter((m) => m.chatbotStep?.expectAnswer)
            .map((m) => m.chatbotStep);
    }

    get expertiseTags() {
        return this.props.thread.livechat_expertise_ids.map((expertise) => ({
            id: expertise.id,
            text: expertise.name,
        }));
    }

    onBlurNote() {
        prettifyMessageContent(this.props.thread.livechatNoteText).then((note) => {
            rpc("/im_livechat/session/update_note", { channel_id: this.props.thread.id, note });
        });
    }

    openVisitorProfile() {
        if (this.ui.isSmall) {
            this.props.thread.channel.chatWindow?.fold();
        } else {
            this.props.thread.channel.openChatWindow({ focus: true });
        }
    }

    get visitorProfileURL() {
        const visitorMember = this.props.thread?.livechatVisitorMember;
        if (visitorMember?.partner_id) {
            return url(`/${startUrl()}/res.partner/${visitorMember.partner_id.id}`);
        }
        return undefined;
    }
}
