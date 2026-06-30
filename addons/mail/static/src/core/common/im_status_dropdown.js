import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ImStatus } from "./im_status";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class ImStatusDropdown extends Component {
    static components = { Dropdown, DropdownItem, ImStatus };
    static props = [];
    static template = "mail.ImStatusDropdown";

    setup() {
        this.store = useService("mail.store");
        this.readableImStatusByCode = {
            online: _t("Online"),
            away: _t("Away"),
            busy: _t("Do Not Disturb"),
            offline: _t("Offline"),
        };
    }

    setManualImStatus(status) {
        rpc("/mail/set_manual_im_status", { status });
    }

    get readableImStatus() {
        const imStatus = this.store.self.im_status || "offline";
        for (const status in this.readableImStatusByCode) {
            if (imStatus.includes(status)) {
                return this.readableImStatusByCode[status];
            }
        }
        return _t("Unknown Status");
    }
}

export function imStatusItem(env) {
    return {
        type: "component",
        contentComponent: ImStatusDropdown,
        sequence: 45,
    };
}

registry.category("user_menuitems").add("im_status", imStatusItem);
