import { CreatePollDialog } from "@mail/core/common/create_poll_dialog";

import { EmojiPicker, useEmojiPickerStoreScroll } from "@web/core/emoji_picker/emoji_picker";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markEventHandled } from "@web/core/utils/misc";
import { Action, ACTION_TAGS, useAction, UseActions } from "@mail/core/common/action";
import { usePopover } from "@web/core/popover/popover_hook";
import { SUGGESTION_DELIMITERS } from "@mail/core/common/suggestion_hook";

export const composerActionsRegistry = registry.category("mail.composer/actions");

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("models").Composer} Composer */
/**
 * @typedef {Object} ComposerActionBaseParams
 * @property {(emoji: string) => void} addEmoji
 * @property {() => boolean} allowUpload
 * @property {() => boolean|undefined} areAllActionsDisabled
 * @property {import("@web/core/dialog/dialog_service").DialogService} dialogService
 * @property {import("@web/core/utils/hooks").Ref} extraActionsRef
 * @property {import("@web/core/utils/hooks").Ref} fileUploaderRef
 * @property {() => boolean} inChatter
 * @property {() => boolean} inDiscussApp
 * @property {() => boolean} inFrontendPortalChatter
 * @property {() => boolean} isFullComposerOpen
 * @property {() => boolean} isSendButtonDisabled
 * @property {() => boolean} isSmall
 * @property {import("@web/core/utils/hooks").Ref} moreActionsRef
 * @property {() => Promise<void>} onClickFullComposer
 * @property {(ev: Event) => void} onClickInsertCannedResponse
 * @property {import("@web/core/utils/hooks").Ref} quickActionsRef
 * @property {() => number|undefined} replyToMessageId
 * @property {(body: ReturnType<import("@odoo/owl").markup>, postData: Object) => Promise<import("models").Message|undefined>} sendGifMessage
 * @property {() => Promise<false | undefined>} sendMessage
 * @property {() => boolean} showFullComposer
 * @property {() => ("message" | "note")} type
 */
/** @typedef {ComposerActionBaseParams & {composer: Composer}} ComposerActionSpecificParams */
/** @typedef {ComposerActionBaseParams & {composer: Composer | (() => Composer)}} UseComposerActionsParams */
/** @typedef {import("@mail/core/common/action").ActionParams<ComposerAction, UseComposerActions_Def> & ComposerActionSpecificParams} ComposerActionParams */
/** @typedef {import("@mail/core/common/action").ActionDefinition<ComposerActionParams, ComposerAction>} ComposerActionDefinition */

/**
 * @param {string} id
 * @param {ComposerActionDefinition} definition
 */
export function registerComposerAction(id, definition) {
    composerActionsRegistry.add(id, definition);
}

export function pickerGetAnchor({
    action,
    extraActionsRef,
    isSmall,
    moreActionsRef,
    quickActionsRef,
}) {
    let anchorEl;
    if (isSmall()) {
        return null;
    }
    if (action.sequenceQuick) {
        anchorEl = quickActionsRef.el;
    } else {
        anchorEl = moreActionsRef.el ?? extraActionsRef.el;
    }
    return anchorEl;
}

registerComposerAction("send-message", {
    btnClass: ({ action }) => (action.isActive ? "o-sendMessageActive o-text-white shadow-sm" : ""),
    condition: ({ composer, inChatter, store }) =>
        (store.env.isSmall && composer.message) || (!inChatter() && !composer.message),
    disabledCondition: ({ isSendButtonDisabled }) => isSendButtonDisabled(),
    icon: "fa fa-paper-plane-o",
    isActive: ({ isSendButtonDisabled }) => !isSendButtonDisabled(),
    name: ({ composer, type }) =>
        composer.message
            ? _t("Save editing")
            : composer.targetThread?.channel
            ? _t("Send")
            : type() === "note"
            ? _t("Log")
            : _t("Send"),
    onSelected: ({ sendMessage }) => sendMessage(),
    sequenceQuick: 30,
    tags: ({ action }) => (action.isActive ? ACTION_TAGS.PRIMARY : undefined),
});
registerComposerAction("add-emoji", {
    actionPanelComponent: EmojiPicker,
    actionPanelComponentProps: ({ action, addEmoji }) => ({
        onSelect: (emoji) => addEmoji(emoji),
        onClose: () => action.actionPanelClose(),
        storeScroll: action.emojiStoreScroll,
    }),
    actionPanelName: _t("Emoji"),
    actionPanelOpen(...args) {
        const anchorEl = pickerGetAnchor(...args);
        this.popover?.open(anchorEl, this.actionPanelComponentProps);
    },
    disabledCondition: ({ areAllActionsDisabled }) => areAllActionsDisabled(),
    icon: "fa fa-smile-o",
    name: _t("Add Emojis"),
    onSelected(params, ev) {
        markEventHandled(ev, "Composer.onClickAddEmoji");
    },
    setup({ store }) {
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
    disabledCondition: ({ areAllActionsDisabled }) => areAllActionsDisabled(),
    condition: ({ allowUpload }) => allowUpload(),
    icon: "fa fa-paperclip",
    name: _t("Attach Files"),
    onSelected: ({ composer, fileUploaderRef }, ev) => {
        fileUploaderRef.el?.click();
        markEventHandled(ev, "composer.clickOnAddAttachment");
        composer.autofocus++;
    },
    sequence: 20,
});
registerComposerAction("open-full-composer", {
    condition: ({ composer, inFrontendPortalChatter, showFullComposer }) =>
        !composer.message &&
        showFullComposer() &&
        composer.targetThread &&
        composer.targetThread.model !== "discuss.channel" &&
        !inFrontendPortalChatter(),
    hasBtnBg: ({ composer, isFullComposerOpen }) =>
        (composer.restoredFromFullComposer && !isFullComposerOpen()) || undefined,
    hotkey: "shift+c",
    icon: "fa fa-expand",
    isActive: ({ composer, isFullComposerOpen }) =>
        (composer.restoredFromFullComposer && !isFullComposerOpen()) || undefined,
    name: _t("Open Full Composer"),
    onSelected: ({ onClickFullComposer }) => onClickFullComposer(),
    sequence: 30,
    tags: ({ composer, isFullComposerOpen }) =>
        composer.restoredFromFullComposer && !isFullComposerOpen()
            ? [ACTION_TAGS.PRIMARY]
            : undefined,
});
registerComposerAction("add-canned-response", {
    condition: ({ composer, store }) =>
        store.hasCannedResponses &&
        composer.targetThread &&
        store.env.services["mail.suggestion"]
            .getSupportedDelimiters(composer.targetThread)
            .find(([delimiter]) => delimiter === SUGGESTION_DELIMITERS.CANNED_RESPONSE),
    icon: "fa fa-file-text-o",
    name: _t("Insert a Canned response"),
    onSelected: ({ onClickInsertCannedResponse }, ev) => onClickInsertCannedResponse(ev),
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
    onSelected: ({ action, composer, dialogService }) =>
        dialogService.add(
            CreatePollDialog,
            { thread: composer.targetThread },
            { rootRef: action.actionRef }
        ),
});

export class ComposerAction extends Action {
    /** @type {(emoji: string) => void} */
    addEmoji;

    /** @type {() => boolean} */
    allowUpload;

    /** @type {() => boolean|undefined} */
    areAllActionsDisabled;

    /** @type {() => Composer} */
    composerFn;

    /** @type {import("@web/core/dialog/dialog_service").DialogService} */
    dialogService;

    /** @type {import("@web/core/utils/hooks").Ref} */
    extraActionsRef;

    /** @type {import("@web/core/utils/hooks").Ref} */
    fileUploaderRef;

    /** @type {() => boolean} */
    inChatter;

    /** @type {() => boolean} */
    inDiscussApp;

    /** @type {() => boolean} */
    inFrontendPortalChatter;

    /** @type {() => boolean} */
    isFullComposerOpen;

    /** @type {() => boolean} */
    isSendButtonDisabled;

    /** @type {() => boolean} */
    isSmall;

    /** @type {import("@web/core/utils/hooks").Ref} */
    moreActionsRef;

    /** @type {() => Promise<void>} */
    onClickFullComposer;

    /** @type {(ev: Event) => void} */
    onClickInsertCannedResponse;

    /** @type {import("@web/core/utils/hooks").Ref} */
    quickActionsRef;

    /** @type {() => number|undefined} */
    replyToMessageId;

    /** @type {(body: ReturnType<import("@odoo/owl").markup>, postData: Object) => Promise<import("models").Message|undefined>} */
    sendGifMessage;

    /** @type {() => Promise<false | undefined>} */
    sendMessage;

    /** @type {() => boolean} */
    showFullComposer;

    /** @type {() => ("message" | "note")} */
    type;

    /**
     * @param {UseComposerActionsParams} param0
     */
    constructor({
        addEmoji,
        allowUpload,
        areAllActionsDisabled,
        composer,
        dialogService,
        extraActionsRef,
        fileUploaderRef,
        inChatter,
        inDiscussApp,
        inFrontendPortalChatter,
        isFullComposerOpen,
        isSendButtonDisabled,
        isSmall,
        moreActionsRef,
        onClickFullComposer,
        onClickInsertCannedResponse,
        quickActionsRef,
        replyToMessageId,
        sendGifMessage,
        sendMessage,
        showFullComposer,
        type,
    }) {
        super(...arguments);
        this.addEmoji = addEmoji;
        this.allowUpload = allowUpload;
        this.areAllActionsDisabled = areAllActionsDisabled;
        this.composerFn = typeof composer === "function" ? composer : () => composer;
        this.dialogService = dialogService;
        this.extraActionsRef = extraActionsRef;
        this.fileUploaderRef = fileUploaderRef;
        this.inChatter = inChatter;
        this.inDiscussApp = inDiscussApp;
        this.inFrontendPortalChatter = inFrontendPortalChatter;
        this.isFullComposerOpen = isFullComposerOpen;
        this.isSendButtonDisabled = isSendButtonDisabled;
        this.isSmall = isSmall;
        this.moreActionsRef = moreActionsRef;
        this.onClickFullComposer = onClickFullComposer;
        this.onClickInsertCannedResponse = onClickInsertCannedResponse;
        this.quickActionsRef = quickActionsRef;
        this.replyToMessageId = replyToMessageId;
        this.sendGifMessage = sendGifMessage;
        this.sendMessage = sendMessage;
        this.showFullComposer = showFullComposer;
        this.type = type;
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
        return Object.assign(super.params, {
            addEmoji: this.addEmoji,
            allowUpload: this.allowUpload,
            areAllActionsDisabled: this.areAllActionsDisabled,
            composer: this.composerFn(),
            dialogService: this.dialogService,
            extraActionsRef: this.extraActionsRef,
            fileUploaderRef: this.fileUploaderRef,
            inChatter: this.inChatter,
            inDiscussApp: this.inDiscussApp,
            inFrontendPortalChatter: this.inFrontendPortalChatter,
            isFullComposerOpen: this.isFullComposerOpen,
            isSendButtonDisabled: this.isSendButtonDisabled,
            isSmall: this.isSmall,
            moreActionsRef: this.moreActionsRef,
            onClickFullComposer: this.onClickFullComposer,
            onClickInsertCannedResponse: this.onClickInsertCannedResponse,
            quickActionsRef: this.quickActionsRef,
            replyToMessageId: this.replyToMessageId,
            sendGifMessage: this.sendGifMessage,
            sendMessage: this.sendMessage,
            showFullComposer: this.showFullComposer,
            type: this.type,
        });
    }
}

/** @typedef {UseActions<ComposerActionParams, ComposerAction>} UseComposerActions_Def */
class UseComposerActions extends UseActions {
    ActionClass = ComposerAction;
}

/**
 * @param {import("@mail/core/common/action").ActionRootRefParam & UseComposerActionsParams} [params0={}]
 * @returns {UseComposerActions_Def}
 */
export function useComposerActions({
    addEmoji,
    allowUpload,
    areAllActionsDisabled,
    composer,
    dialogService,
    extraActionsRef,
    fileUploaderRef,
    inChatter,
    inDiscussApp,
    inFrontendPortalChatter,
    isFullComposerOpen,
    isSendButtonDisabled,
    isSmall,
    moreActionsRef,
    onClickFullComposer,
    onClickInsertCannedResponse,
    quickActionsRef,
    replyToMessageId,
    rootRef,
    sendGifMessage,
    sendMessage,
    showFullComposer,
    type,
} = {}) {
    return useAction(composerActionsRegistry, UseComposerActions, ComposerAction, {
        addEmoji,
        allowUpload,
        areAllActionsDisabled,
        composer,
        dialogService,
        extraActionsRef,
        fileUploaderRef,
        inChatter,
        inDiscussApp,
        inFrontendPortalChatter,
        isFullComposerOpen,
        isSendButtonDisabled,
        isSmall,
        moreActionsRef,
        onClickFullComposer,
        onClickInsertCannedResponse,
        quickActionsRef,
        rootRef,
        replyToMessageId,
        sendGifMessage,
        sendMessage,
        showFullComposer,
        type,
    });
}
