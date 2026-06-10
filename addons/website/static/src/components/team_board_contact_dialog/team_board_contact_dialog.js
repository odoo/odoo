import { Component, markup } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { addLoadingEffect } from "@web/core/utils/ui";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export const contactActionRegistry = registry.add("website.team_board.contact_actions");

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

        this.notifications = useService("notification");

        this.actions = contactActionRegistry.getAll().filter((action) => action);
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

contactActionRegistry.add("send_message", {
    label: _t("Send a message"),
    sequence: 0,
    primary: true,
    execute: async (event, component) => {
        const stopLoadingEffect = addLoadingEffect(event.currentTarget);
        const result = await rpc("/website/team_board_contact");

        if (!result.ok) {
            component.notifications.add("Could not send your message", { type: "danger" });
            stopLoadingEffect();
            return;
        }

        component.notifications.add("Your message has been sent", { type: "success" });
        component.props.close();
    },
});
