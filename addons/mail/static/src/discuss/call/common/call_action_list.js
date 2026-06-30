import { Component, onWillRender, toRaw, useRef } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { CALL_PROMOTE_FULLSCREEN } from "@mail/discuss/call/common/thread_model_patch";
import { ActionList } from "@mail/core/common/action_list";
import { ACTION_TAGS } from "@mail/core/common/action";

export class CallActionList extends Component {
    static components = { ActionList };
    static props = ["thread", "compact?"];
    static template = "discuss.CallActionList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.pipService = useService("discuss.pip_service");
        this.callActions = useCallActions({ thread: () => this.props.thread });
        this.more = useRef("more");
        this.root = useRef("root");
        this.popover = usePopover(Tooltip, {
            position: "top-middle",
        });
        onWillRender(() => {
            const partition = toRaw(this.callActions).partition;
            const other = partition.other.filter((a) => !a.tags.includes(ACTION_TAGS.CALL_LAYOUT));
            const group2 = [];
            for (const groupActions of partition.group) {
                const filtered = groupActions.filter(
                    (a) => !a.tags.includes(ACTION_TAGS.CALL_LAYOUT)
                );
                const sequenceGroup = filtered[0].sequenceGroup;
                const maxQuickActions = sequenceGroup === 200 ? 1 : 4;
                const quickActions = filtered.slice(0, maxQuickActions);
                const moreActions = filtered.slice(maxQuickActions);
                const newGroup = moreActions?.length
                    ? [
                          ...quickActions,
                          this.callActions.more(
                              {
                                  actions: moreActions,
                                  dropdownMenuClass: "m-0 mb-1",
                                  dropdownPosition: "top-end",
                                  name: this.MORE,
                              },
                              sequenceGroup
                          ),
                      ]
                    : quickActions;
                group2.push(newGroup);
            }
            this.actions = [...group2, other];
        });
    }

    /** @deprecated */
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

    onMouseenterMore() {
        if (this.isPromotingFullscreen) {
            this.popover.open(this.more.el, { tooltip: _t("Enter full screen!") });
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
