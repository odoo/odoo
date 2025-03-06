import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { ImStatus } from "../common/im_status";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from "@web/core/network/rpc";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class UserStatusPanel extends Component {
    static template = "mail.UserStatusPanel";
    static components = { ImStatus, Dropdown, DropdownItem };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.readableImStatus = {
            online: "Online",
            away: "Away",
            busy: "Do Not Disturb",
            offline: "Offline",
        };
    }

    forceImstatus(status) {
        rpc("/mail/force_im_status", { status: status === "online" ? null : status });
        rpc("/discuss/settings/mute", { minutes: status === "busy" ? -1 : false });
        this.store.self.im_status = status;
    }
}
