import { Component, computed, signal, toRaw, types, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { callButtonPropsInline, useCallActions } from "@mail/discuss/call/common/call_actions";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { ActionList } from "@mail/core/common/action_list";
import { attClassObjectToString } from "@mail/utils/common/format";

export class CallActionList extends Component {
    static components = { ActionList };
    static template = "discuss.CallActionList";

    more = signal(null);
    root = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            channel: types.instanceOf(this.store["discuss.channel"]),
            className: types.string().optional(),
            compact: types.boolean().optional(),
            pipExtraActions: types.array().optional(),
        });
        this.rtc = useService("discuss.rtc");
        this.pipService = useService("discuss.pip_service");
        this.callActions = useCallActions(this.callActionsParams);
        this.popover = usePopover(Tooltip, {
            position: "top-middle",
        });
        this.actions = computed(() => {
            const partition = toRaw(this.callActions).partition;
            const other = partition.other;
            const group2 = [];
            for (const groupActions of partition.group) {
                const sequenceGroup = groupActions[0].sequenceGroup;
                const hasPipActions = sequenceGroup === 200 && this.props.pipExtraActions;
                const pipActions = hasPipActions ? this.props.pipExtraActions : [];
                const maxQuickActions = pipActions.length > 0 ? 1 : 4;
                const quickActions = groupActions.slice(0, maxQuickActions);
                const moreActions = [...pipActions, ...groupActions.slice(maxQuickActions)];
                const newGroup = moreActions?.length
                    ? [
                          ...quickActions,
                          this.callActions.more(
                              this.callActionsParams,
                              {
                                  actions: moreActions,
                                  dropdownMenuClass: attClassObjectToString({
                                      "m-0 mb-1 overflow-x-hidden": true,
                                      "o-discuss-CallActionList-menu": Boolean(
                                          this.env.inMeetingView
                                      ),
                                  }),
                                  dropdownPosition: "top-end",
                                  name: this.MORE,
                                  propsInline: callButtonPropsInline,
                              },
                              sequenceGroup
                          ),
                      ]
                    : quickActions;
                group2.push(newGroup);
            }
            return [...group2, other];
        });
    }

    get callActionsParams() {
        return { channel: () => this.props.channel };
    }

    get MORE() {
        return _t("More");
    }

    get isSmall() {
        return Boolean(this.props.compact && this.rtc.isFullscreen);
    }
}
