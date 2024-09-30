import { Component, useRef, useState } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { StatusSettings } from "@mail/core/public_web/status_settings";

export const discussSidebarItemsRegistry = registry.category("mail.discuss_sidebar_items");

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class UserStatusPanel extends Component {
    static template = "mail.UserStatusPanel";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.statusRef = useRef("status");
        this.statusSettingsPopover = usePopover(StatusSettings, {
            position: "bottom-start",
            fixedPosition: true,
        });
    }

    onStatusClicked() {
        if (this.statusSettingsPopover.isOpen) {
            this.statusSettingsPopover.close();
        } else {
            this.statusSettingsPopover.open(this.statusRef.el);
        }
    }
}
