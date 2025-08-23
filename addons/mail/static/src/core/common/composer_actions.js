import { toRaw, useComponent, useEffect, useRef, useState } from "@odoo/owl";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markEventHandled } from "@web/core/utils/misc";
import { Action } from "./action";

export const composerActionsRegistry = registry.category("mail.composer/actions");

/** @typedef {import("@odoo/owl").Component} Component */

/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */

/**
 * @typedef {Object} ComposerActionSpecificDefinition
 * @property {boolean|(comp: Component) => boolean} [condition=true]
 * @property {boolean} [isPicker]
 * @property {string|(comp: Component) => string} [pickerName]
 * @property {boolean|(comp: Component) => boolean} [sequenceGroup]
 * @property {boolean|(comp: Component) => boolean} [sequenceQuick]
 */

/**
 * @typedef {ActionDefinition & ComposerActionSpecificDefinition} ComposerActionDefinition
 */

/**
 * @param {string} id
 * @param {ComposerActionDefinition} definition
 */
export function registerComposerAction(id, definition) {
    composerActionsRegistry.add(id, definition);
}

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
    if (toRaw(previousPicker) === toRaw(action.picker)) {
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

registerComposerAction("send-message", {
    btnClass(component) {
        if (this.isActive) {
            return "o-sendMessageActive o-text-white shadow-sm";
        }
        return "";
    },
    condition: (component) =>
        !component.env.inChatter && (!component.props.composer.message || component.ui.isSmall),
    disabledCondition: (component) => component.isSendButtonDisabled,
    icon: "fa fa-paper-plane-o",
    iconLarge: "fa fa-lg fa-paper-plane-o",
    isActive: (component) => component.sendMessageState.active,
    name(component) {
        if (component.props.composer.message) {
            return _t("Save editing");
        }
        if (component.thread?.model === "discuss.channel") {
            return _t("Send");
        }
        return component.props.type === "note" ? _t("Log") : _t("Send");
    },
    onSelected: (component) => component.sendMessage(),
    setup: (component) => {
        component.sendMessageState = useState({ active: false });
        useEffect(
            () => {
                component.sendMessageState.active = !component.isSendButtonDisabled;
            },
            () => [component.isSendButtonDisabled]
        );
    },
    sequenceQuick: 30,
});
registerComposerAction("add-emoji", {
    icon: "fa fa-smile-o",
    iconLarge: "fa fa-lg fa-smile-o",
    isPicker: true,
    pickerName: _t("Emoji"),
    name: _t("Add Emojis"),
    onSelected: (component, action, ev) => {
        pickerOnClick(component, action, ev);
        markEventHandled(ev, "Composer.onClickAddEmoji");
    },
    setup(component) {
        pickerSetup(this, () =>
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
});
registerComposerAction("upload-files", {
    condition: (component) => component.allowUpload,
    icon: "fa fa-paperclip",
    iconLarge: "fa fa-lg fa-paperclip",
    name: _t("Attach Files"),
    onSelected: (component, action, ev) => {
        component.fileUploaderRef.el?.click();
        const composer = toRaw(component.props.composer);
        markEventHandled(ev, "composer.clickOnAddAttachment");
        composer.autofocus++;
    },
    setup: (component) => {
        component.fileUploaderRef = useRef("file-uploader");
    },
    sequence: 20,
});
registerComposerAction("open-full-composer", {
    condition: (component) =>
        component.props.showFullComposer &&
        component.thread &&
        component.thread.model !== "discuss.channel" &&
        !component.env.inFrontendPortalChatter,
    hotkey: "shift+c",
    icon: "fa fa-expand",
    iconLarge: "fa fa-lg fa-expand",
    name: _t("Open Full Composer"),
    onSelected: (component) => component.onClickFullComposer(),
    sequence: 30,
});
registerComposerAction("add-canned-response", {
    condition: (component) =>
        component.store.hasCannedResponses &&
        component.thread &&
        component.env.services["mail.suggestion"]
            .getSupportedDelimiters(component.thread)
            .find(([delimiter]) => delimiter === "::"),
    icon: "fa fa-file-text-o",
    iconLarge: "fa fa-lg fa-file-text-o",
    name: _t("Insert a Canned response"),
    onSelected: (component, action, ev) => component.onClickInsertCannedResponse(ev),
    sequence: 5,
});

class ComposerAction extends Action {
    get condition() {
        return composerActionsInternal.condition(this._component, this.id, this.explicitDefinition);
    }

    get disabledCondition() {
        return (
            composerActionsInternal.disabledCondition(
                this._component,
                this.id,
                this.explicitDefinition
            ) ?? super.disabledCondition
        );
    }

    get isPicker() {
        return this.explicitDefinition.isPicker;
    }

    get pickerName() {
        return typeof this.explicitDefinition.pickerName === "function"
            ? this.explicitDefinition.pickerName(this._component)
            : this.explicitDefinition.pickerName;
    }

    get sequenceGroup() {
        return typeof this.explicitDefinition.sequenceGroup === "function"
            ? this.explicitDefinition.sequenceGroup(this._component)
            : this.explicitDefinition.sequenceGroup;
    }

    get sequenceQuick() {
        return typeof this.explicitDefinition.sequenceQuick === "function"
            ? this.explicitDefinition.sequenceQuick(this._component)
            : this.explicitDefinition.sequenceQuick;
    }
}

export const composerActionsInternal = {
    condition(component, id, action) {
        if (!action?.condition) {
            return true;
        }
        return typeof action.condition === "function"
            ? action.condition(component)
            : action.condition;
    },
    disabledCondition(component, id, action) {
        if (!action?.disabledCondition) {
            return false;
        }
        return undefined;
    },
};

export function useComposerActions() {
    const component = useComponent();
    const transformedActions = composerActionsRegistry
        .getEntries()
        .map(([id, action]) => new ComposerAction(component, id, action));
    for (const action of transformedActions) {
        action.setup();
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
                .filter((a) => !a.sequenceQuick && !a.sequenceGroup)
                .sort((a1, a2) => a1.sequence - a2.sequence);
            return { quick, group, other, pickers };
        },
    });
    component.getActivePicker = () => state.activePicker;
    component.setActivePicker = (newActivePicker) => (state.activePicker = newActivePicker);
    return state;
}
