import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { escape, sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class MessageSeenIndicatorPopover extends Component {
    static template = "mail.MessageSeenIndicatorPopover";
    static props = ["message", "close?"];

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    openModal() {
        this.dialog.add(MessageSeenIndicatorDialog, { message: this.props.message });
    }

    get AND_X_OTHERS() {
        return sprintf(escape(_t("and %(channel_members_number)s others")), {
            channel_members_number: this.props.message.channelMemberHaveSeen.length - 10,
        });
    }
}

class MessageSeenIndicatorDialog extends Component {
    static components = { Dialog };
    static template = "mail.MessageSeenIndicatorPopover.dialog";
    static props = ["message", "close?"];
}
