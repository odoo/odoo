import { toRaw, useComponent, useEffect, useRef, useState } from "@odoo/owl";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markEventHandled } from "@web/core/utils/misc";
import { Action, UseActions } from "@mail/core/common/action";
import { useService } from "@web/core/utils/hooks";

export const composerActionsRegistry = registry.category("mail.composer/actions");

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */
/** @typedef {import("models").Composer} Composer */
/**
 * @typedef {Object} ComposerActionSpecificDefinition
 * @property {boolean|(comp: Component) => boolean} [condition=true]
 * @property {boolean} [isPicker]
 * @property {string|(comp: Component) => string} [pickerName]
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
    btnClass: ({ action }) => (action.isActive ? "o-sendMessageActive o-text-white shadow-sm" : ""),
    condition: ({ composer, owner, store }) =>
        (store.env.isSmall && composer.message) || (!owner.env.inChatter && !composer.message),
    disabledCondition: ({ owner }) => owner.isSendButtonDisabled,
    icon: "fa fa-paper-plane-o",
    isActive: ({ owner }) => owner.sendMessageState.active,
    name: ({ composer, owner }) =>
        composer.message
            ? _t("Save editing")
            : composer.targetThread?.model === "discuss.channel"
            ? _t("Send")
            : owner.props.type === "note"
            ? _t("Log")
            : _t("Send"),
    onSelected: ({ owner }) => owner.sendMessage(),
    setup: ({ owner }) => {
        owner.sendMessageState = useState({ active: false });
        useEffect(
            () => {
                owner.sendMessageState.active = !owner.isSendButtonDisabled;
            },
            () => [owner.isSendButtonDisabled]
        );
    },
    sequenceQuick: 30,
});
registerComposerAction("add-emoji", {
    icon: "fa fa-smile-o",
    isPicker: true,
    pickerName: _t("Emoji"),
    name: _t("Add Emojis"),
    onSelected({ owner }, ev) {
        pickerOnClick(owner, this, ev);
        markEventHandled(ev, "Composer.onClickAddEmoji");
    },
    setup({ owner }) {
        pickerSetup(this, () =>
            useEmojiPicker(
                undefined,
                {
                    onSelect: (emoji) => owner.addEmoji(emoji),
                    onClose: () => owner.setActivePicker(null),
                },
                { arrow: false }
            )
        );
    },
    sequenceQuick: 20,
});
registerComposerAction("upload-files", {
    condition: ({ owner }) => owner.allowUpload,
    icon: "fa fa-paperclip",
    name: _t("Attach Files"),
    onSelected: ({ composer: comp, owner }, ev) => {
        owner.fileUploaderRef.el?.click();
        const composer = toRaw(comp);
        markEventHandled(ev, "composer.clickOnAddAttachment");
        composer.autofocus++;
    },
    setup: ({ owner }) => (owner.fileUploaderRef = useRef("file-uploader")),
    sequence: 20,
});
registerComposerAction("open-full-composer", {
    condition: ({ composer, owner }) =>
        owner.props.showFullComposer &&
        composer.targetThread &&
        composer.targetThread.model !== "discuss.channel" &&
        !owner.env.inFrontendPortalChatter,
    hotkey: "shift+c",
    icon: "fa fa-expand",
    name: _t("Open Full Composer"),
    onSelected: ({ owner }) => owner.onClickFullComposer(),
    sequence: 30,
});
registerComposerAction("add-canned-response", {
    condition: ({ composer, store }) =>
        store.hasCannedResponses &&
        composer.targetThread &&
        store.env.services["mail.suggestion"]
            .getSupportedDelimiters(composer.targetThread)
            .find(([delimiter]) => delimiter === "::"),
    icon: "fa fa-file-text-o",
    name: _t("Insert a Canned response"),
    onSelected: ({ owner }, ev) => owner.onClickInsertCannedResponse(ev),
    sequence: 5,
});

export class ComposerAction extends Action {
    /** @type {() => Composer} */
    composerFn;

    /**
     * @param {Object} param0
     * @param {Composer|() => Composer} composer
     */
    constructor({ composer }) {
        super(...arguments);
        this.composerFn = typeof composer === "function" ? composer : () => composer;
    }

    get params() {
        return Object.assign(super.params, { composer: this.composerFn() });
    }

    get isPicker() {
        return this.definition.isPicker;
    }

    get pickerName() {
        return typeof this.definition.pickerName === "function"
            ? this.definition.pickerName(this._component)
            : this.definition.pickerName;
    }
}

class UseComposerActions extends UseActions {
    get partition() {
        const res = super.partition;
        const actions = this.transformedActions.filter((action) => action.condition);
        const groupedPickers = Object.groupBy(
            actions.filter((a) => a.isPicker),
            (a) => (a.sequenceQuick ? "quick" : "other")
        );
        groupedPickers.quick?.sort((a1, a2) => a1.sequenceQuick - a2.sequenceQuick);
        groupedPickers.other?.sort((a1, a2) => a1.sequence - a2.sequence);
        const pickers = (groupedPickers.other ?? []).concat(groupedPickers.quick ?? []);
        return Object.assign(res, { pickers });
    }
}

/**
 * @param {Object} [params0={}]
 * @param {Composer|() => Composer} composer
 */
export function useComposerActions({ composer } = {}) {
    const component = useComponent();
    const transformedActions = composerActionsRegistry
        .getEntries()
        .map(
            ([id, definition]) => new ComposerAction({ owner: component, id, definition, composer })
        );
    for (const action of transformedActions) {
        action.setup();
    }
    const state = useState(
        new UseComposerActions(component, transformedActions, useService("mail.store"))
    );
    component.getActivePicker = () => state.activePicker;
    component.setActivePicker = (newActivePicker) => (state.activePicker = newActivePicker);
    return state;
}
