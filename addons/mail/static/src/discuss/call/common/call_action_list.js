import { useRef } from "@web/owl2/utils";
import { Component, computed, props, toRaw, types } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { ActionList } from "@mail/core/common/action_list";
import { ACTION_TAGS } from "@mail/core/common/action";
import { attClassObjectToString } from "@mail/utils/common/format";
import { CALL_PROMOTE_FULLSCREEN } from "@mail/discuss/call/common/discuss_channel_model_patch";

export class CallActionList extends Component {
    static components = { ActionList };
    static template = "discuss.CallActionList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            channel: types.instanceOf(this.store["discuss.channel"].Class),
            className: types.string().optional(),
            compact: types.boolean().optional(),
            pipExtraActions: types.array().optional(),
        });
        this.rtc = useService("discuss.rtc");
        this.pipService = useService("discuss.pip_service");
        this.callActions = useCallActions(this.callActionsParams);
        this.more = useRef("more");
        this.root = useRef("root");
        this.popover = usePopover(Tooltip, {
            position: "top-middle",
        });
        this.actions = computed(() => {
            const partition = toRaw(this.callActions).partition;
            const other = partition.other.filter((a) => !a.tags.includes(ACTION_TAGS.CALL_LAYOUT));
            const group2 = [];
            let disconnectGroupIndex = -1;
            for (const groupActions of partition.group) {
                const filtered = groupActions.filter(
                    (a) => !a.tags.includes(ACTION_TAGS.CALL_LAYOUT)
                );
                const sequenceGroup = filtered[0].sequenceGroup;
                const hasPipActions = sequenceGroup === 200 && this.props.pipExtraActions;
                const pipActions = hasPipActions ? this.props.pipExtraActions : [];
                const maxQuickActions = pipActions.length > 0 ? 1 : 4;
                const quickActions = filtered.slice(0, maxQuickActions);
                const moreActions = [...pipActions, ...filtered.slice(maxQuickActions)];
                const newGroup = moreActions?.length
                    ? [
                          ...quickActions,
                          this.callActions.more(
                              this.callActionsParams,
                              {
                                  actions: moreActions,
                                  dropdownMenuClass: "m-0 mb-1 overflow-x-hidden",
                                  dropdownPosition: "top-end",
                                  name: this.MORE,
                              },
                              sequenceGroup
                          ),
                      ]
                    : quickActions;
                if (sequenceGroup >= 300 && disconnectGroupIndex === -1) {
                    disconnectGroupIndex = group2.length;
                }
                group2.push(newGroup);
            }
            // Gather the layout actions (Fullscreen, Adjust view, Picture in Picture) into a "More"
            // menu placed between Raise Hand and the end-call button.
            const layoutActions = toRaw(this.callActions).actions.filter((a) =>
                a.tags.includes(ACTION_TAGS.CALL_LAYOUT)
            );
            if (layoutActions.length) {
                const layoutGroup = [
                    this.callActions.more(
                        this.callActionsParams,
                        {
                            actions: [layoutActions],
                            // Pulse the toggle to nudge fullscreen, as the Fullscreen action that
                            // used to carry the pulse now lives inside this menu.
                            btnClass: ({ channel }) =>
                                attClassObjectToString({
                                    "o-discuss-CallActionList-pulse": Boolean(
                                        channel?.promoteFullscreen ===
                                            CALL_PROMOTE_FULLSCREEN.ACTIVE
                                    ),
                                }),
                            dropdownMenuClass:
                                "o-discuss-CallActionList-callLayout m-0 mb-1 overflow-x-hidden",
                            dropdownPosition: "top-end",
                            id: "call-layout",
                            name: this.MORE,
                        },
                        "call-layout"
                    ),
                ];
                group2.splice(
                    disconnectGroupIndex === -1 ? group2.length : disconnectGroupIndex,
                    0,
                    layoutGroup
                );
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
