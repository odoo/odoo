import { Component, computed, signal, toRaw, types, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";
import {
    ActionList,
    CircleInlineAction,
    DropdownAction,
    InlineAction,
} from "@mail/core/common/action_list";
import { ACTION_TAGS } from "@mail/core/common/action";
import { attClassObjectToString } from "@mail/utils/common/format";
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
 * Round button of the call controls. Its size and its neutral grays come from the call bar
 * (call_action_list.scss) rather than a button variant or the call theme.
 */
export class CallControlInlineAction extends InlineAction {
    get classObj() {
        return {
            ...super.classObj,
            "o-discuss-CallControl d-inline-flex align-items-center justify-content-center": true,
        };
    }

    /** None of the looks of the action list's inline buttons, with or without a background. */
    get coreClass() {
        return {
            ...super.coreClass,
            "btn-group-item o-inline": false,
            "btn-group-item": true,
            "o-hasBtnBg": false,
        };
    }

    get colorClass() {
        return {
            "o-discuss-CallControl-neutral": true,
            // Raising a hand and sharing the screen stand out, unlike an open menu or panel.
            "o-discuss-CallControl-selected": this.action.tags.includes(ACTION_TAGS.SUCCESS),
        };
    }

    get iconClass() {
        return { ...super.iconClass, "o-discuss-CallControl-icon": true };
    }

    get borderClass() {
        return { "border-0": true };
    }

    get marginClass() {
        return { "m-0": true };
    }

    get paddingClass() {
        return { "p-0": true };
    }

    get roundnessClass() {
        return { "rounded-pill": true };
    }

    get themeClass() {
        return {};
    }
}

/** Button opening a "More" menu, narrower than the other call controls. */
export class CallMoreInlineAction extends CallControlInlineAction {
    get classObj() {
        return { ...super.classObj, "o-discuss-CallControl-more": true };
    }
}

/** Microphone or camera toggle, sharing a pill with its settings: neutral if on, red if off. */
export class CallToggleInlineAction extends CallControlInlineAction {
    get colorClass() {
        const isOff =
            this.action.tags.includes(ACTION_TAGS.DANGER) ||
            (this.action.id === "camera-on" && !this.action.isActive);
        return { "o-discuss-CallControl-toggle": !isOff, "o-discuss-CallControl-off": isOff };
    }
}

/** Settings chevron of the microphone or the camera, which shares the pill of its toggle. */
export class CallSettingsInlineAction extends CallControlInlineAction {
    get classObj() {
        return { ...super.classObj, "o-discuss-CallControl-settings": true };
    }

    get colorClass() {
        return {};
    }

    get iconClass() {
        return {
            ...super.iconClass,
            "o-discuss-CallControl-icon": false,
            "o-discuss-CallControl-chevron transition-base": true,
        };
    }

    get paddingClass() {
        return { "ps-0 pe-1 py-0": true };
    }
}

/** Button to leave the call, a wider red pill. */
export class LeaveCallInlineAction extends CallControlInlineAction {
    get classObj() {
        return { ...super.classObj, "o-discuss-CallControl-leave": true };
    }

    get colorClass() {
        return { "btn-danger": true };
    }
}

/**
 * Item of the menus of the call controls, without the call theme's look: the menu gives the
 * colors. In a meeting, it matches the meeting's larger bar.
 */
export class CallMenuDropdownAction extends DropdownAction {
    get alignmentClass() {
        if (!this.env.inMeetingView) {
            return super.alignmentClass;
        }
        return { "d-flex align-items-center dropdown-item_active_noarrow text-start gap-3": true };
    }

    get colorClass() {
        return { ...super.colorClass, "btn-secondary": false };
    }

    get iconClass() {
        if (!this.env.inMeetingView) {
            return super.iconClass;
        }
        return { "oi-fw": this.props.fw, "fs-3": true };
    }

    get labelClass() {
        return { ...super.labelClass, "fs-6": Boolean(this.env.inMeetingView) };
    }

    get paddingClass() {
        if (!this.env.inMeetingView) {
            return super.paddingClass;
        }
        return { "o-px-3_5 o-py-2_5": true };
    }

    get themeClass() {
        return {};
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

/**
 * Picks the component of the call controls. Join and reject keep the look of the buttons to join
 * or leave a call, @see getCallActionComponent, as they may carry a label.
 *
 * @type {import("@mail/core/common/action_list").GetActionComponent}
 */
export function getCallControlComponent(params) {
    const { action, dropdown, inline } = params;
    if (dropdown) {
        return CallMenuDropdownAction;
    }
    if (!inline) {
        return undefined;
    }
    if (action.id === "disconnect") {
        return LeaveCallInlineAction;
    }
    if (action.tags.includes(ACTION_TAGS.JOIN_LEAVE_CALL)) {
        return getCallActionComponent(params);
    }
    if (action.definition?.isMoreAction) {
        return CallMoreInlineAction;
    }
    if (["quick-video-settings", "quick-voice-settings"].includes(action.id)) {
        return CallSettingsInlineAction;
    }
    if (["camera-on", "deafen", "mute"].includes(action.id)) {
        return CallToggleInlineAction;
    }
    return CallControlInlineAction;
}

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
                                          "o-discuss-CallActionList-menu m-0 mb-1 border-0 shadow overflow-x-hidden": true,
                                          "o-inMeetingView": Boolean(this.env.inMeetingView),
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
                                    "o-discuss-CallActionList-callLayout o-discuss-CallActionList-menu m-0 mb-1 border-0 shadow overflow-x-hidden": true,
                                    "o-inMeetingView": Boolean(this.env.inMeetingView),
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
            },
            { equals: nestedShallowEqual }
        );
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
                              "o-discuss-CallActionList-menu m-0 mb-1 border-0 shadow overflow-x-hidden": true,
                              "o-inMeetingView": Boolean(this.env.inMeetingView),
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
        return getCallControlComponent(params);
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
