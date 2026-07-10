import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { Component, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class DiscussInvitationDialog extends Component {
    static components = { Dialog };
    static template = "mail.DiscussInvitationDialog";

    setup() {
        super.setup(...arguments);
        this.props = useProps({
            close: t.function(),
            channel: t.instanceOf(DiscussChannel),
            onConfirm: t.function(),
        });
        this.store = useService("mail.store");
    }

    get channel() {
        return this.props.channel;
    }

    get body() {
        return _t(
            "Welcome to %(channel_name)s! You have been invited to join this discussion channel.",
            { channel_name: this.props.channel.displayName }
        );
    }

    get title() {
        return _t("Invitation to join %(channel_name)s", {
            channel_name: this.props.channel?.displayName ?? _t("a meeting"),
        });
    }

    onClickConfirm() {
        this.props.onConfirm();
        this.props.close();
    }
}
