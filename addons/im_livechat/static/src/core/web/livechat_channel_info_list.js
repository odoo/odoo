import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { Component, onMounted } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class LivechatChannelInfoList extends Component {
    static components = { ActionPanel, TagsList };
    static template = "im_livechat.channelInfoList";
    static props = ["thread"];

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.store = useService("mail.store");
        onMounted(async () => {
            const data = await rpc("/im_livechat/visitor", {
                channel_id: this.props.thread.id,
                visitor_id: this.props.thread.livechat_visitor_id?.id,
            });
            this.store.insert(data);
        });
    }

    get chatbotAnswers() {
        return this.props.thread.messages
            .filter((m) => m.chatbotStep?.selectedAnswer)
            .map((m) => m.chatbotStep.selectedAnswer);
    }

    get expertiseTags() {
        return (
            this.props.thread.livechat_expertise_ids.map((expertise) => {
                return {
                    id: expertise.id,
                    text: expertise.name,
                    colorIndex: 0,
                    className: "me-1 mb-1",
                };
            }) || []
        );
    }

    get recentConversations() {
        return Object.values(this.store.Thread.records).filter((channel) => {
            return (
                channel.livechat_visitor_id?.eq(this.props.thread.livechat_visitor_id) &&
                channel?.id !== this.props.thread.id
            );
        });
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

    updateLivechatStatus(status) {
        if (this.props.thread.livechat_status === status) {
            return;
        }
        this.orm
            .write("discuss.channel", [this.props.thread.id], {
                livechat_status: status,
            })
            .then(() => {
                this.props.thread.livechat_status = status;
            });
    }

    onBlurNote() {
        this.orm.write("discuss.channel", [this.props.thread.id], {
            note: this.props.thread.note,
        });
    }
}
