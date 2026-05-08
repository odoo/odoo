import { useComponent, useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { CreatePollDialog } from "@mail/core/common/create_poll_dialog";

import { toRaw } from "@odoo/owl";
import { EmojiPicker, useEmojiPickerStoreScroll } from "@web/core/emoji_picker/emoji_picker";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markEventHandled } from "@web/core/utils/misc";
import { Action, ACTION_TAGS, useAction, UseActions } from "@mail/core/common/action";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";

export const composerActionsRegistry = registry.category("mail.composer/actions");

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */
/** @typedef {import("models").Composer} Composer */
/**
 * @typedef {ActionDefinition} ComposerActionDefinition
 */

/**
 * @param {string} id
 * @param {ComposerActionDefinition} definition
 */
export function registerComposerAction(id, definition) {
    composerActionsRegistry.add(id, definition);
}

export function pickerGetAnchor({ action, owner }) {
    let anchorEl;
    if (owner.ui.isSmall) {
        return null;
    }
    if (!anchorEl) {
        if (action.sequenceQuick) {
            anchorEl = owner.quickActionsRef.el;
        } else {
            anchorEl = owner.moreActionsRef.el ?? owner.extraActionsRef.el;
        }
    }
    return anchorEl;
}

export function pickerSetup() {
    const component = useComponent();
    component.quickActionsRef = useRef("quick-actions");
    component.moreActionsRef = useRef("more-actions");
    component.extraActionsRef = useRef("extra-actions");
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
            : composer.targetThread?.channel
            ? _t("Send")
            : owner.props.type === "note"
            ? _t("Log")
            : _t("Send"),
    onSelected: ({ owner }) => owner.sendMessage(),
    setup: ({ owner }) => {
        owner.sendMessageState = useState({ active: false });
        useLayoutEffect(
            () => {
                owner.sendMessageState.active = !owner.isSendButtonDisabled;
            },
            () => [owner.isSendButtonDisabled]
        );
    },
    sequenceQuick: 30,
    tags: ({ action }) => (action.isActive ? ACTION_TAGS.PRIMARY : undefined),
});
registerComposerAction("add-emoji", {
    actionPanelComponent: EmojiPicker,
    actionPanelComponentProps: ({ action, owner }) => ({
        onSelect: (emoji) => owner.addEmoji(emoji),
        onClose: () => action.actionPanelClose(),
        storeScroll: action.emojiStoreScroll,
    }),
    actionPanelName: _t("Emoji"),
    actionPanelOpen(...args) {
        const anchorEl = pickerGetAnchor(...args);
        this.popover?.open(anchorEl, this.actionPanelComponentProps);
    },
    disabledCondition: ({ owner }) => owner.areAllActionsDisabled,
    icon: "fa fa-smile-o",
    name: _t("Add Emojis"),
    onSelected(params, ev) {
        markEventHandled(ev, "Composer.onClickAddEmoji");
    },
    setup({ store }) {
        pickerSetup();
        if (store.env.services.ui.isSmall) {
            return;
        }
        this.emojiStoreScroll = useEmojiPickerStoreScroll();
        this.popover = usePopover(EmojiPicker, {
            arrow: false,
            onClose: () => this.actionPanelClose(),
        });
    },
    sequenceQuick: 20,
});
registerComposerAction("upload-files", {
    disabledCondition: ({ owner }) => owner.areAllActionsDisabled,
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
        !composer.message &&
        owner.props.showFullComposer &&
        composer.targetThread &&
        composer.targetThread.model !== "discuss.channel" &&
        !owner.env.inFrontendPortalChatter,
    hasBtnBg: ({ composer, owner }) =>
        (composer.restoredFromFullComposer && !owner.state.isFullComposerOpen) || undefined,
    hotkey: "shift+c",
    icon: "fa fa-expand",
    isActive: ({ composer, owner }) =>
        (composer.restoredFromFullComposer && !owner.state.isFullComposerOpen) || undefined,
    name: _t("Open Full Composer"),
    onSelected: ({ owner }) => owner.onClickFullComposer(),
    sequence: 30,
    tags: ({ composer, owner }) =>
        composer.restoredFromFullComposer && !owner.state.isFullComposerOpen
            ? [ACTION_TAGS.PRIMARY]
            : undefined,
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
registerComposerAction("start-poll", {
    name: _t("Start a poll"),
    icon: "oi oi-view-cohort",
    condition: ({ composer, store }) => {
        if (!store.self_user || store.self_user.share || composer.message) {
            return false;
        }
        return ["channel", "group"].includes(composer.targetThread?.channel?.channel_type);
    },
    onSelected: ({ composer, owner }) =>
        owner.dialogService.add(CreatePollDialog, { thread: composer.targetThread }),
    setup: ({ owner }) => {
        owner.dialogService = useService("dialog");
    },
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

    /**
     * @param {Object} param0
     * @param {Composer|() => Composer} composer
     */
    _disabledCondition({ composer }) {
        if (composer.restoredFromFullComposer && this.id !== "open-full-composer") {
            return true;
        }
        return super._disabledCondition(...arguments);
    }

    get params() {
        return Object.assign(super.params, { composer: this.composerFn() });
    }
}

class UseComposerActions extends UseActions {
    ActionClass = ComposerAction;
}

/**
 * @param {Object} [params0={}]
 * @param {Composer|() => Composer} composer
 */
export function useComposerActions({ composer } = {}) {
    return useAction(composerActionsRegistry, UseComposerActions, ComposerAction, {
        composer,
    });
}
