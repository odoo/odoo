import { Component, useRef } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { CallPopover } from "@mail/discuss/call/common/call_popover";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { CallActionButton } from "@mail/discuss/call/common/call_action_button";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { CALL_PROMOTE_FULLSCREEN } from "@mail/discuss/call/common/thread_model_patch";

export class CallActionList extends Component {
    static components = { CallPopover, CallActionButton };
    static props = ["thread", "compact?"];
    static template = "discuss.CallActionList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.pipService = useService("discuss.pip_service");
        this.callActions = useCallActions();
        this.more = useRef("more");
        this.root = useRef("root");
        this.popover = usePopover(Tooltip, {
            position: "top-middle",
        });
    }

    get isPromotingFullscreen() {
        return Boolean(
            !this.env.pipWindow &&
                this.props.thread.promoteFullscreen === CALL_PROMOTE_FULLSCREEN.ACTIVE
        );
    }

    get MORE() {
        return _t("More");
    }

    get isOfActiveCall() {
        return Boolean(this.props.thread.eq(this.rtc.channel));
    }

    get isSmall() {
        return Boolean(this.props.compact && this.rtc.state.isFullscreen);
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
    async onClickToggleAudioCall(ev, { camera = false } = {}) {
        await this.rtc.toggleCall(this.props.thread, { camera });
    }

    onMouseenterMore() {
        if (this.isPromotingFullscreen) {
            this.popover.open(this.more.el, { tooltip: _t("Full Screen!") });
            this.props.thread.promoteFullscreen = CALL_PROMOTE_FULLSCREEN.DISCARDED;
        }
    }

    onMouseleaveMore() {
        if (this.popover.isOpen) {
            this.popover.close();
        }
    }

    onClickMore() {
        if (this.popover.isOpen) {
            this.popover.close();
        }
    }
}
