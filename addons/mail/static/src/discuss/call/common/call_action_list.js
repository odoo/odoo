import { Component, computed, signal, toRaw, types, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { ActionList } from "@mail/core/common/action_list";
import { ACTION_TAGS } from "@mail/core/common/action";
import { attClassObjectToString } from "@mail/utils/common/format";

/**
 * What a small screen keeps in its bar; everything else goes into "More". "deafen" is there
 * because it swaps places with "mute": without it the bar loses its audio control once deafened.
 */
const SMALL_SCREEN_BAR_ACTION_IDS = [
    "camera-on",
    "deafen",
    "mute",
    "quick-video-settings",
    "quick-voice-settings",
];

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
            /** Action groups a caller folds into the small-screen "More" instead of rendering. */
            extraMoreActionGroups: types.array().optional(),
            pipExtraActions: types.array().optional(),
        });
        this.rtc = useService("discuss.rtc");
        this.ui = useService("ui");
        this.pipService = useService("discuss.pip_service");
        this.callActions = useCallActions(this.callActionsParams);
        this.popover = usePopover(Tooltip, {
            position: "top-middle",
        });
        this.actions = computed(() => {
            const partition = toRaw(this.callActions).partition;
            if (this.ui.isSmall) {
                return this.smallScreenActions(partition);
            }
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
                                  dropdownMenuClass: attClassObjectToString({
                                      "m-0 mb-1 overflow-x-hidden": true,
                                      "o-discuss-CallActionList-menu": Boolean(
                                          this.env.inMeetingView
                                      ),
                                  }),
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
                            dropdownMenuClass: attClassObjectToString({
                                "o-discuss-CallActionList-callLayout m-0 mb-1 overflow-x-hidden": true,
                                "o-discuss-CallActionList-menu o-inMeetingView": Boolean(
                                    this.env.inMeetingView
                                ),
                            }),
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

    /**
     * The groups of a small screen's bar, in bar order. Everything folds into a single "More": the
     * wide bar's one menu per group is more chrome than a phone fits.
     *
     * @param {{ group: Array<Array>, other: Array }} partition
     */
    smallScreenActions(partition) {
        const barGroups = [];
        const moreGroups = [];
        const joinLeave = [];
        for (const groupActions of partition.group) {
            const kept = [];
            const moved = [];
            for (const action of groupActions) {
                if (action.tags.includes(ACTION_TAGS.JOIN_LEAVE_CALL)) {
                    joinLeave.push(action);
                } else if (SMALL_SCREEN_BAR_ACTION_IDS.includes(action.id)) {
                    kept.push(action);
                } else {
                    moved.push(action);
                }
            }
            if (kept.length) {
                barGroups.push(kept);
            }
            if (moved.length) {
                moreGroups.push(moved);
            }
        }
        if (this.props.pipExtraActions?.length) {
            moreGroups.push(this.props.pipExtraActions);
        }
        // The layout actions (Fullscreen, Adjust view, Picture in Picture) carry no sequenceGroup.
        if (partition.other.length) {
            moreGroups.push(partition.other);
        }
        // A meeting hands its side actions over rather than opening a second "More" beside this.
        moreGroups.push(...(this.props.extraMoreActionGroups ?? []));
        const moreGroup = moreGroups.length
            ? [
                  this.callActions.more(
                      this.callActionsParams,
                      {
                          actions: moreGroups,
                          dropdownMenuClass: attClassObjectToString({
                              "m-0 mb-1 overflow-x-hidden": true,
                              "o-discuss-CallActionList-menu": Boolean(this.env.inMeetingView),
                          }),
                          dropdownPosition: "top-end",
                          id: "small-screen-more",
                          name: this.MORE,
                      },
                      "small-screen-more"
                  ),
              ]
            : [];
        return [...barGroups, moreGroup, joinLeave].filter((group) => group.length);
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
