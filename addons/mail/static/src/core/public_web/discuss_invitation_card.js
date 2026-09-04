import { Component, useProps, t, proxy, signal } from "@odoo/owl";
import { useLayoutEffect } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";
import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";

export class DiscussInvitationCard extends Component {
    static template = "mail.DiscussInvitationCard";
    static components = { AvatarStack };

    setup() {
        super.setup(...arguments);
        this.props = useProps({
            channel: t.instanceOf(DiscussChannel),
            canConfirm: t.boolean().optional(true),
            onConfirm: t.function(),
            channelIcon: t.string().optional("forum"),
        });
        this.state = proxy({
            isDescriptionUnfolded: false,
            isDescriptionLong: false,
        });
        this.description = signal();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        useLayoutEffect(
            (isDescriptionUnfolded, description) => {
                const descriptionEl = this.description();
                this.state.isDescriptionLong =
                    !isDescriptionUnfolded &&
                    description &&
                    descriptionEl?.scrollWidth > descriptionEl?.clientWidth;
            },
            () => [this.state.isDescriptionUnfolded, this.channel.description]
        );
    }

    get channel() {
        return this.props.channel;
    }

    unfoldDescription() {
        if (this.state.isDescriptionUnfolded) {
            return;
        }
        this.state.isDescriptionUnfolded = true;
    }

    get shouldShowMoreDescription() {
        return this.state.isDescriptionLong;
    }

    get isMeeting() {
        return this.channel.default_display_mode === "video_full_screen";
    }
}
