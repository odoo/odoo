import { Component, useState } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "./call_actions";

export class CallActionList extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["thread", "fullscreen", "compact?"];
    static template = "discuss.CallActionList";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.rtc = useState(useService("discuss.rtc"));
        this.callActions = useCallActions();
    }

    get MORE() {
        return _t("More");
    }

<<<<<<< master
||||||| 125ad36dda97a89500e289d1f555c2f8e18faf83
    get moreActions() {
        const acts = [];
        acts.push({
            id: "raiseHand",
            name: !this.rtc.state?.selfSession.raisingHand ? _t("Raise Hand") : _t("Lower Hand"),
            icon: "fa fa-fw fa-hand-paper-o",
            onSelect: (ev) => this.onClickRaiseHand(ev),
        });
        if (isMobileOS) {
            acts.push({
                id: "shareScreen",
                name: !this.rtc.state.sendScreen ? _t("Share Screen") : _t("Stop Sharing Screen"),
                icon: "fa fa-fw fa-desktop",
                onSelect: () => this.rtc.toggleVideo("screen"),
            });
        }
        if (!this.props.fullscreen.isActive) {
            acts.push({
                id: "fullScreen",
                name: _t("Enter Full Screen"),
                icon: "fa fa-fw fa-arrows-alt",
                onSelect: () => this.props.fullscreen.enter(),
            });
        } else {
            acts.push({
                id: "exitFullScreen",
                name: _t("Exit Full Screen"),
                icon: "fa fa-fw fa-compress",
                onSelect: () => this.props.fullscreen.exit(),
            });
        }
        return acts;
    }

=======
    get moreActions() {
        const acts = [];
        acts.push({
            id: "raiseHand",
            name: !this.rtc.state?.selfSession.raisingHand ? _t("Raise Hand") : _t("Lower Hand"),
            icon: "fa fa-fw fa-hand-paper-o",
            onSelect: (ev) => this.onClickRaiseHand(ev),
        });
        if (!isMobileOS()) {
            acts.push({
                id: "shareScreen",
                name: !this.rtc.state.sendScreen ? _t("Share Screen") : _t("Stop Sharing Screen"),
                icon: "fa fa-fw fa-desktop",
                onSelect: () => this.rtc.toggleVideo("screen"),
            });
        }
        if (!this.props.fullscreen.isActive) {
            acts.push({
                id: "fullScreen",
                name: _t("Enter Full Screen"),
                icon: "fa fa-fw fa-arrows-alt",
                onSelect: () => this.props.fullscreen.enter(),
            });
        } else {
            acts.push({
                id: "exitFullScreen",
                name: _t("Exit Full Screen"),
                icon: "fa fa-fw fa-compress",
                onSelect: () => this.props.fullscreen.exit(),
            });
        }
        return acts;
    }

>>>>>>> 1472097cb92096919c2a54a9aa2700ec7392c03b
    get isOfActiveCall() {
        return Boolean(this.props.thread.eq(this.rtc.state?.channel));
    }

    get isSmall() {
        return Boolean(this.props.compact && !this.props.fullscreen.isActive);
    }

    get isMobileOS() {
        return isMobileOS();
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickRejectCall(ev) {
        if (this.rtc.state.hasPendingRequest) {
            return;
        }
        await this.rtc.leaveCall(this.props.thread);
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickToggleAudioCall(ev) {
        await this.rtc.toggleCall(this.props.thread);
    }
}
