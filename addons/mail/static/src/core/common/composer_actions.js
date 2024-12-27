import { toRaw, useComponent, useEffect, useRef, useState } from "@odoo/owl";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markEventHandled } from "@web/core/utils/misc";

export const composerActionsRegistry = registry.category("mail.composer/actions");

export function pickerOnClick(component, action, ev) {
    let anchorEl;
    if (component.ui.isSmall) {
        anchorEl = component.pickerTargetRef.el;
    } else if (!anchorEl) {
        if (action.sequenceQuick) {
            anchorEl = component.quickActionsRef.el;
        } else {
            anchorEl = component.moreActionsRef.el ?? action.ref.el;
        }
    }
    const previousPicker = component.getActivePicker();
    previousPicker?.close();
    if (previousPicker === action.picker) {
        component.setActivePicker(null);
    } else {
        component.setActivePicker(action.picker);
        component.getActivePicker().open({ el: anchorEl });
    }
}

export function pickerSetup(action, func) {
    const component = useComponent();
    component.pickerTargetRef = useRef("picker-target");
    component.quickActionsRef = useRef("quick-actions");
    component.moreActionsRef = useRef("more-actions");
    action.ref = useRef(action.id);
    action.picker = func();
}

composerActionsRegistry
    .add("send-message", {
        btnClass: (component) => {
            if (component.sendMessageState.active) {
                return "o-sendMessageActive o-text-white";
            }
            return "";
        },
        condition: (component) =>
            component.props.mode !== "extended" ||
            (component.props.messageToReplyTo?.message &&
                component.props.composer.thread.notEq(
                    component.props.messageToReplyTo.message.thread
                )),
        disabledCondition: (component) => component.isSendButtonDisabled,
        icon: "fa fa-paper-plane-o",
        name(component) {
            if (component.props.composer.message) {
                return _t("Save editing");
            }
            if (component.thread?.model === "discuss.channel") {
                return _t("Send");
            }
            return component.props.type === "note" ? _t("Log") : _t("Send");
        },
        onClick: (component) => component.sendMessage(),
        setup: () => {
            const component = useComponent();
            component.sendMessageState = useState({ active: false });
            useEffect(
                () => {
                    component.sendMessageState.active = !component.isSendButtonDisabled;
                },
                () => [component.isSendButtonDisabled]
            );
        },
        sequenceQuick: 30,
    })
    .add("add-emoji", {
        icon: "fa fa-smile-o",
        isPicker: true,
        pickerName: _t("Emoji"),
        name: _t("Add Emojis"),
        onClick: (component, action, ev) => {
            pickerOnClick(component, action, ev);
            markEventHandled(ev, "Composer.onClickAddEmoji");
        },
        setup: (action) => {
            const component = useComponent();
            pickerSetup(action, () =>
                useEmojiPicker(
                    undefined,
                    {
                        onSelect: (emoji) => component.addEmoji(emoji),
                        onClose: () => component.setActivePicker(null),
                    },
                    { arrow: false }
                )
            );
        },
        sequenceQuick: 20,
    })
    .add("upload-files", {
        condition: (component) => {
            const thread = component.thread ?? component.message?.thread;
            if (!thread?.allow_public_upload && component.store.self.type === "guest") {
                return false;
            }
            return !(
                component.thread?.channel_type === "whatsapp" &&
                component.props.composer.attachments.length > 0
            );
        },
        icon: "fa fa-paperclip",
        name: _t("Attach Files"),
        onClick: (component, action, ev) => {
            component.fileUploaderRef.el?.click();
            const composer = toRaw(component.props.composer);
            markEventHandled(ev, "composer.clickOnAddAttachment");
            composer.autofocus++;
        },
        setup: () => {
            const component = useComponent();
            component.fileUploaderRef = useRef("file-uploader");
        },
        sequence: 20,
    })
    .add("open-full-composer", {
        condition: (component) =>
            component.props.showFullComposer &&
            component.thread &&
            component.thread.model !== "discuss.channel" &&
            !component.env.inFrontendPortalChatter,
        hotkey: "shift+c",
        icon: "fa fa-expand",
        name: _t("Open Full Composer"),
        onClick: (component) => component.onClickFullComposer(),
        sequence: 30,
    });

function transformAction(component, id, action) {
    return {
        get btnClass() {
            return typeof action.btnClass === "function"
                ? action.btnClass(component)
                : action.btnClass;
        },
        component: action.component,
        get componentProps() {
            return action.componentProps?.(component, this);
        },
        get condition() {
            if (!action?.condition) {
                return true;
            }
            return typeof action.condition === "function"
                ? action.condition(component)
                : action.condition;
        },
        get disabledCondition() {
            return action.disabledCondition?.(component);
        },
        get hotkey() {
            return typeof action.hotkey === "function" ? action.hotkey(component) : action.hotkey;
        },
        get icon() {
            return typeof action.icon === "function" ? action.icon(component) : action.icon;
        },
        id,
        isPicker: action.isPicker,
        get name() {
            return typeof action.name === "function" ? action.name(component) : action.name;
        },
        onClick(ev) {
            action.onClick?.(component, this, ev);
        },
        get pickerName() {
            return typeof action.pickerName === "function"
                ? action.pickerName(component)
                : action.pickerName;
        },
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence(component)
                : action.sequence;
        },
        get sequenceGroup() {
            return typeof action.sequenceGroup === "function"
                ? action.sequenceGroup(component)
                : action.sequenceGroup;
        },
        get sequenceQuick() {
            return typeof action.sequenceQuick === "function"
                ? action.sequenceQuick(component)
                : action.sequenceQuick;
        },
        setup: action.setup,
    };
}

export function useComposerActions() {
    const component = useComponent();
    const transformedActions = composerActionsRegistry
        .getEntries()
        .map(([id, action]) => transformAction(component, id, action));
    for (const action of transformedActions) {
        if (action.setup) {
            action.setup(action);
        }
    }
    const state = useState({
        get actions() {
            return transformedActions
                .filter((action) => action.condition)
                .sort((a1, a2) => a1.sequence - a2.sequence);
        },
        get partition() {
            const actions = transformedActions.filter((action) => action.condition);
            const groupedPickers = Object.groupBy(
                actions.filter((a) => a.isPicker),
                (a) => (a.sequenceQuick ? "quick" : "other")
            );
            groupedPickers.quick?.sort((a1, a2) => a1.sequenceQuick - a2.sequenceQuick);
            groupedPickers.other?.sort((a1, a2) => a1.sequence - a2.sequence);
            const pickers = (groupedPickers.other ?? []).concat(groupedPickers.quick ?? []);
            const quick = actions
                .filter((a) => a.sequenceQuick)
                .sort((a1, a2) => a1.sequenceQuick - a2.sequenceQuick);
            const grouped = actions.filter((a) => a.sequenceGroup);
            const groups = {};
            for (const a of grouped) {
                if (!(a.sequenceGroup in groups)) {
                    groups[a.sequenceGroup] = [];
                }
                groups[a.sequenceGroup].push(a);
            }
            const sortedGroups = Object.entries(groups).sort(
                ([groupId1], [groupId2]) => groupId1 - groupId2
            );
            for (const [, actions] of sortedGroups) {
                actions.sort((a1, a2) => a1.sequence - a2.sequence);
            }
            const group = sortedGroups.map(([groupId, actions]) => actions);
            const other = actions
                .filter((a) => !a.sequenceQuick & !a.sequenceGroup)
                .sort((a1, a2) => a1.sequence - a2.sequence);
            return { quick, group, other, pickers };
        },
    });
    component.getActivePicker = () => state.activePicker;
    component.setActivePicker = (newActivePicker) => (state.activePicker = newActivePicker);
    return state;
}
