import { Component, computed, signal, toRaw, types, untrack, useEffect, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { usePopover } from "@web/core/popover/popover_hook";
import { ActionList, CircleInlineAction, InlineAction } from "@mail/core/common/action_list";
import { ACTION_TAGS } from "@mail/core/common/action";
import { attClassObjectToString } from "@mail/utils/common/format";
import { FullscreenTooltip } from "@mail/discuss/call/common/fullscreen_tooltip";
import { nestedShallowEqual } from "@mail/utils/common/signal";

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

/** Button to join or leave a call as a pill, which shows its name next to its icon. */
export class PillCallInlineAction extends InlineAction {
    get classObj() {
        return { ...super.classObj, "text-nowrap pe-2 mx-1": true };
    }

    get roundnessClass() {
        return { "rounded-pill": true };
    }

    get showLabel() {
        return true;
    }
}

/** Button to join the call again, with the camera as last time, which its icon tells. */
export class JoinBackInlineAction extends PillCallInlineAction {
    get label() {
        return _t("Join");
    }
}

/**
 * Picks the component of the inline buttons to join or leave a call: circles, except the button
 * to join the call again, and the button to reject next to it, which are pills.
 *
 * @type {import("@mail/core/common/action_list").GetActionComponent}
 */
export function getCallActionComponent({ action, actions, inline }) {
    if (!inline || !action.tags.includes(ACTION_TAGS.JOIN_LEAVE_CALL)) {
        return undefined;
    }
    if (action.id === "join-back") {
        return JoinBackInlineAction;
    }
    if (action.id === "reject" && actions?.actions.some(({ id }) => id === "join-back")) {
        return PillCallInlineAction;
    }
    return CircleInlineAction;
}

/** Buttons of the bar of a meeting, which get bigger while it is fullscreen. */
const meetingAction = (Base) =>
    class extends Base {
        get isFullscreen() {
            return this.store.rtc.isFullscreen;
        }

        get paddingClass() {
            return { ...super.paddingClass, "px-1 py-2": this.isFullscreen };
        }

        get iconClass() {
            return {
                ...super.iconClass,
                "oi-lg": this.isFullscreen,
                "py-1": this.isFullscreen && !this.isCircle,
            };
        }
    };

/** Meeting variant of each component, made once so that its buttons are not remounted. */
const meetingActions = new WeakMap();

/**
 * @param {typeof InlineAction} Base
 * @returns {typeof InlineAction}
 */
function getMeetingAction(Base) {
    if (!meetingActions.has(Base)) {
        meetingActions.set(Base, meetingAction(Base));
    }
    return meetingActions.get(Base);
}

export const MeetingInlineAction = getMeetingAction(InlineAction);

export class CallActionList extends Component {
    static components = { ActionList };
    static template = "discuss.CallActionList";

    callLayoutMoreAction = signal(null);
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
        this.fullscreenHintPopover = usePopover(FullscreenTooltip, {
            closeOnClickAway: false,
            closeOnEscape: false,
            position: "top-middle",
        });
        this.actions = computed(
            () => {
                const partition = toRaw(this.callActions).partition;
                if (this.ui.isSmall) {
                    return this.smallScreenActions(partition);
                }
                const other = partition.other.filter(
                    (a) => !a.tags.includes(ACTION_TAGS.CALL_LAYOUT)
                );
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
                    const moreAction = this.callActions.more(
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
                    );
                    this.callLayoutMoreAction.set(moreAction);
                    const layoutGroup = [moreAction];
                    group2.splice(
                        disconnectGroupIndex === -1 ? group2.length : disconnectGroupIndex,
                        0,
                        layoutGroup
                    );
                } else {
                    this.callLayoutMoreAction.set(null);
                }
                return [...group2, other];
            },
            { equals: nestedShallowEqual }
        );

        useEffect(() => {
            this.actions();
            const moreAction = this.callLayoutMoreAction();
            const referenceEl = moreAction?.actionRef();
            const showHint = this.rtc.showFullscreenHint;
            const isOpen = untrack(() => this.fullscreenHintPopover.isOpen);
            if (moreAction && referenceEl && showHint && !isOpen) {
                this.fullscreenHintPopover.open(referenceEl, {});
            } else if (!showHint && isOpen) {
                this.fullscreenHintPopover.close();
            }
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

    /** @type {import("@mail/core/common/action_list").GetActionComponent} */
    getActionComponent(params) {
        if (!params.inline) {
            return undefined;
        }
        const callActionComponent = getCallActionComponent(params);
        if (this.env.inMeetingView) {
            return getMeetingAction(callActionComponent ?? InlineAction);
        }
        return callActionComponent;
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
