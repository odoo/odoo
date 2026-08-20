import { useSubEnv } from "@web/owl2/utils";
import { Component, signal } from "@odoo/owl";

import { ActionList } from "@mail/core/common/action_list";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { TalkingAudioBars } from "@mail/discuss/call/common/talking_audio_bars";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class CallMenu extends Component {
    static template = "discuss.CallMenu";
    static components = { ActionList, Dropdown, TalkingAudioBars };

    root = signal.ref();

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.callActions = useCallActions({ channel: () => this.rtc.channel });
        useSubEnv({ inCallMenu: true });
        this.dropdownState = useDropdownState();
        this.isEnterprise = odoo.info && odoo.info.isEnterprise;
    }

    get icon() {
        return "mic";
    }
}

registry.category("systray").add("discuss.CallMenu", { Component: CallMenu }, { sequence: 105 });
