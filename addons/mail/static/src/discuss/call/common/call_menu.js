import { Component, signal, useEffect, usePlugin } from "@odoo/owl";

import { ActionList } from "@mail/core/common/action_list";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { MicrophoneWarning } from "@mail/discuss/call/common/microphone_warning";
import { TalkingAudioBars } from "@mail/discuss/call/common/talking_audio_bars";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { PopoverPlugin } from "@web/core/popover/popover_plugin";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class CallMenu extends Component {
    static template = "discuss.CallMenu";
    static components = { ActionList, Dropdown, TalkingAudioBars };

    menuRef = signal.ref();
    root = signal.ref();

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        useAncestors({ inCallMenu: true });
        this.callActions = useCallActions({ channel: () => this.rtc.channel });
        this.dropdownState = useDropdownState();
        this.isEnterprise = odoo.info && odoo.info.isEnterprise;
        const popover = usePlugin(PopoverPlugin);
        useEffect(() => {
            const isDropdownOpen = this.dropdownState.isOpen;
            const target = isDropdownOpen ? this.menuRef() : this.root();
            const hasWarning =
                this.rtc.showMicrophoneSilentWarning || this.rtc.showTalkWhileMutedSuggestion;
            if (!hasWarning || this.rtc.isSelfCallViewOpen || !target) {
                return;
            }
            return popover.add(
                target,
                MicrophoneWarning,
                {},
                {
                    closeOnClickAway: false,
                    closeOnEscape: false,
                    position: isDropdownOpen ? "left-start" : "bottom",
                    setActiveElement: false,
                }
            );
        });
    }

    get lastSelfAction() {
        return this.rtc.callActions.find((action) => action.id === this.rtc.lastSelfCallAction);
    }

    get lastSelfActionAttClass() {
        const { lastSelfAction } = this;
        if (!lastSelfAction) {
            return {};
        }
        return {
            "text-danger": lastSelfAction.isActive && lastSelfAction.tags.includes("DANGER"),
            "text-success": lastSelfAction.isActive && lastSelfAction.tags.includes("SUCCESS"),
        };
    }

    get icon() {
        const res = this.lastSelfAction?.icon;
        return (typeof res === "function" ? res() : res) ?? "mic";
    }
}

registry.category("systray").add("discuss.CallMenu", { Component: CallMenu }, { sequence: 105 });
