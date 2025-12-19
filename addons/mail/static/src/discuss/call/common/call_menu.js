import { Component, useSubEnv } from "@odoo/owl";

import { ActionList } from "@mail/core/common/action_list";
import { useCallActions } from "@mail/discuss/call/common/call_actions";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class CallMenu extends Component {
    static props = [];
    static template = "discuss.CallMenu";
    static components = { ActionList, Dropdown };
    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.callActions = useCallActions({ channel: () => this.rtc.channel });
        useSubEnv({ inCallMenu: true });
        this.dropdownState = useDropdownState();
        this.isEnterprise = odoo.info && odoo.info.isEnterprise;
    }

    get icon() {
        const res = this.rtc.callActions.find(
            (action) => action.id === this.rtc.lastSelfCallAction
        )?.icon;
        return (typeof res === "function" ? res() : res) ?? "fa fa-microphone";
    }
}

registry.category("systray").add("discuss.CallMenu", { Component: CallMenu }, { sequence: 100 });
