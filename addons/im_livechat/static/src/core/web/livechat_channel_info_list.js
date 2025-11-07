import { TranscriptSender } from "@im_livechat/core/common/transcript_sender";
import { ExpertiseTagsAutocomplete } from "@im_livechat/core/web/expertise_tags_autocomplete";
import { ConversationTagEdit } from "@im_livechat/core/web/livechat_conversation_tag_edit";

import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { prettifyMessageContent } from "@mail/utils/common/format";

import { Component, useEffect, useRef, useSubEnv } from "@odoo/owl";

import { startUrl } from "@web/core/browser/router";
import { rpc } from "@web/core/network/rpc";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { TagsList } from "@web/core/tags_list/tags_list";

export class LivechatChannelInfoList extends Component {
    static components = { ActionPanel, TagsList, ExpertiseTagsAutocomplete, TranscriptSender };
    static template = "im_livechat.LivechatChannelInfoList";
    static props = ["thread"];

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.tagEditPopover = usePopover(ConversationTagEdit, {
            closeOnClickAway: true,
            position: "left",
            useBottomSheet: this.ui.isSmall,
        });
        this.tagsContainer = useRef("tagsContainer");
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

    get conversationTags() {
        return this.props.thread.livechat_conversation_tag_ids.map((tag) => ({
            id: tag.id,
            text: tag.name,
            colorIndex: tag.color,
            className: "me-1 mb-1",
        }));
    }

    get expectAnswerSteps() {
        return this.props.thread.messages
            .filter((m) => m.chatbotStep?.expectAnswer)
            .map((m) => m.chatbotStep);
    }

    /** @deprecated */
    get expertiseTags() {
        return this.props.thread.livechat_expertise_ids.map((expertise) => ({
            id: expertise.id,
            text: expertise.name,
            colorIndex: 0,
            className: "me-1 mb-1",
        }));
    }

    onBlurNote() {
        prettifyMessageContent(this.props.thread.livechatNoteText).then((note) => {
            rpc("/im_livechat/session/update_note", { channel_id: this.props.thread.id, note });
        });
    }

    onClickEditTags(ev) {
        this.tagEditPopover.open(this.tagsContainer.el, {
            thread: this.props.thread,
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
        const visitorMember = this.props.thread?.livechatVisitorMember;
        if (visitorMember?.partner_id) {
            return url(`/${startUrl()}/res.partner/${visitorMember.partner_id.id}`);
        }
        return undefined;
    }
}
