import { Component, useProps, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { DiscussInvitationCard } from "./discuss_invitation_card";

export class DiscussInvitation extends Component {
    static template = "mail.DiscussInvitation";

    static components = { Dialog, DiscussInvitationCard };

    setup() {
        super.setup(...arguments);
        this.props = useProps({
            channel: t.instanceOf(DiscussChannel),
            onConfirm: t.function(),
            close: t.function(),
        });
        this.store = useService("mail.store");
    }

    get channel() {
        return this.props.channel;
    }

    get title() {
        return this.channel?.displayName
            ? _t("You have been invited to join %(channel_name)s", {
                  channel_name: this.channel.displayName,
              })
            : _t("You have been invited to join a channel");
    }

    onClickConfirm() {
        this.props.onConfirm();
        this.props.close();
    }
}
