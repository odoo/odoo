import { Component, markup } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { addLoadingEffect } from "@web/core/utils/ui";
import { useRef } from "@web/owl2/utils";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export class TeamBoardDialog extends Component {
    static template = "website.TeamBoardContactDialog";
    static components = { Dialog };
    static props = {
        content: { type: String },
        close: { type: Function },
        img: { type: String },
    };

    setup() {
        this.content = markup(this.props.content);

        this.sendButtonRef = useRef("website.TeamBoardContactDialogSendButton");

        this.notifications = useService("notification");
    }

    async sendMessage() {
        const stopLoadingEffect = addLoadingEffect(this.sendButtonRef.el);
        const result = await rpc("/website/team_board_contact");

        if (!result.ok) {
            this.notifications.add("Could not send your message", { type: "danger" });
            stopLoadingEffect();
            return;
        }

        this.notifications.add("Your message has been sent", { type: "success" });
        this.props.close();
    }

    handleKeyup(event) {
        const hotkey = getActiveHotkey(event);
        if (hotkey === "escape") {
            this.props.close();
        }
    }

    handleClick(event) {
        if (event.target.classList.contains("modal")) {
            this.props.close();
        }
    }
}
