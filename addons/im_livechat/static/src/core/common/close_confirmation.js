import { Component } from "@odoo/owl";
import { useAutofocus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class CloseConfirmation extends Component {
    static template = "im_livechat.CloseConfirmation";
    static props = ["onCloseConfirmationDialog", "onClickLeaveConversation", "channelName?"];

    setup() {
        useAutofocus({ refName: "confirm" });
    }

    get confirmationMessage() {
        if (this.props.channelName) {
            return _t(
                "Leaving will end the live chat with %(channel_name)s. Are you sure you want to continue?",
                { channel_name: this.props.channelName }
            );
        }
        return _t("Leaving will end the live chat. Do you want to proceed?");
    }

    onKeydown(ev) {
        if (ev.key === "Escape") {
            this.props.onCloseConfirmationDialog();
        } else if (ev.key === "Enter") {
            this.props.onClickLeaveConversation();
        }
    }
}
