import { CreatePollDialog } from "@mail/core/common/create_poll_dialog";

import { EmojiPicker, useEmojiPickerStoreScroll } from "@web/core/emoji_picker/emoji_picker";

import { Action, ACTION_TAGS, useAction, UseActions } from "@mail/core/common/action";
import { SUGGESTION_DELIMITERS } from "@mail/core/common/suggestion_hook";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export const composerActionsRegistry = registry.category("mail.composer/actions");

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("models").Composer} Composer */
/**
 * @typedef {Object} ComposerActionSpecificParams
 * @property {(value: any, postData?: Object, extraData?: Object) => Promise<void>} _sendMessage
 * @property {boolean} active
 * @property {(emoji: string) => void} addEmoji
 * @property {boolean} allowUpload
 * @property {boolean} areAllActionsDisabled
 * @property {Composer} composer
 * @property {import("@odoo/owl").Signal<HTMLElement>} extraActionsRef
 * @property {import("@odoo/owl").Signal<HTMLButtonElement>} fileUploaderRef
 * @property {boolean} inChatter
 * @property {boolean} inDiscussApp
 * @property {boolean} inFrontendPortalChatter
 * @property {boolean} inKnowledge
 * @property {boolean} isFullComposerOpen
 * @property {boolean} isSendButtonDisabled
 * @property {import("@odoo/owl").Signal<HTMLElement>} moreActionsRef
 * @property {() => void} onClickFullComposer
 * @property {(ev: Event) => void} onClickInsertCannedResponse
 * @property {() => void} onclickWhatsAppChat
 * @property {number} projectSharingId
 * @property {import("@odoo/owl").Signal<HTMLElement>} quickActionsRef
 * @property {() => void} sendMessage
 * @property {boolean} showFullComposer
 * @property {string} type
 * @property {Object} voiceRecorder
 * @property {Object} voiceTranscription
 */
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
    moreActionsRef,
    quickActionsRef,
    store,
}) {
    if (store.env.services.ui.isSmall) {
        return null;
    }
    if (action.sequenceQuick) {
        return quickActionsRef();
    } else {
        return moreActionsRef() ?? extraActionsRef();
    }
}

registerComposerAction("send-message", {
    btnClass: ({ action }) => (action.isActive ? "o-sendMessageActive o-text-white shadow-sm" : ""),
    condition: ({ composer, inChatter, store }) =>
        (store.env.services.ui.isSmall && composer.message) || (!inChatter && !composer.message),
    disabledCondition: ({ isSendButtonDisabled }) => isSendButtonDisabled,
    icon: "fa fa-paper-plane-o",
    isActive: ({ isSendButtonDisabled }) => !isSendButtonDisabled,
    name: ({ composer, type }) =>
        composer.message
            ? _t("Save editing")
            : composer.targetThread?.channel
            ? _t("Send")
            : type === "note"
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
    disabledCondition: ({ areAllActionsDisabled }) => areAllActionsDisabled,
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
    disabledCondition: ({ areAllActionsDisabled }) => areAllActionsDisabled,
    condition: ({ allowUpload }) => allowUpload,
    icon: "fa fa-paperclip",
    name: _t("Attach Files"),
    onSelected: ({ composer, fileUploaderRef }, ev) => {
        fileUploaderRef()?.click();
        markEventHandled(ev, "composer.clickOnAddAttachment");
        composer.autofocus++;
    },
    sequence: 20,
});
registerComposerAction("open-full-composer", {
    condition: ({ composer, inFrontendPortalChatter, showFullComposer }) =>
        !composer.message &&
        showFullComposer &&
        composer.targetThread &&
        composer.targetThread.model !== "discuss.channel" &&
        !inFrontendPortalChatter,
    hasBtnBg: ({ composer, isFullComposerOpen }) =>
        (composer.restoredFromFullComposer && !isFullComposerOpen) || undefined,
    hotkey: "shift+c",
    icon: "fa fa-expand",
    isActive: ({ composer, isFullComposerOpen }) =>
        (composer.restoredFromFullComposer && !isFullComposerOpen) || undefined,
    name: _t("Open Full Composer"),
    onSelected: ({ onClickFullComposer }) => onClickFullComposer(),
    sequence: 30,
    tags: ({ composer, isFullComposerOpen }) =>
        composer.restoredFromFullComposer && !isFullComposerOpen
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
    name: _t("Insert Canned Response"),
    onSelected: ({ onClickInsertCannedResponse }, ev) => onClickInsertCannedResponse(ev),
    sequence: 5,
});
registerComposerAction("create-poll", {
    name: _t("Create Poll"),
    icon: "oi oi-view-cohort",
    condition: ({ composer, store }) => {
        if (!store.self_user || store.self_user.share || composer.message) {
            return false;
        }
        return ["channel", "group"].includes(composer.targetThread?.channel?.channel_type);
    },
    onSelected({ composer }) {
        this.dialogService.add(
            CreatePollDialog,
            { thread: composer.targetThread },
            { rootRef: this.actionRef }
        );
    },
    setup() {
        this.dialogService = useService("dialog");
    },
});

export class ComposerAction extends Action {
    /** @type {(value: any, postData?: Object, extraData?: Object) => Promise<void>} */
    _sendMessage;
    /** @type {() => boolean} */
    activeFn;
    /** @type {(emoji: string) => void} */
    addEmoji;
    /** @type {() => boolean} */
    allowUploadFn;
    /** @type {() => boolean} */
    areAllActionsDisabledFn;
    /** @type {() => Composer} */
    composerFn;
    /** @type {import("@odoo/owl").Signal<HTMLElement>} */
    extraActionsRef;
    /** @type {import("@odoo/owl").Signal<HTMLButtonElement>} */
    fileUploaderRef;
    /** @type {boolean} */
    inChatter;
    /** @type {boolean} */
    inDiscussApp;
    /** @type {boolean} */
    inFrontendPortalChatter;
    /** @type {boolean} */
    inKnowledge;
    /** @type {() => boolean} */
    isFullComposerOpenFn;
    /** @type {() => boolean} */
    isSendButtonDisabledFn;
    /** @type {import("@odoo/owl").Signal<HTMLElement>} */
    moreActionsRef;
    /** @type {() => void} */
    onClickFullComposer;
    /** @type {(ev: Event) => void} */
    onClickInsertCannedResponse;
    /** @type {() => void} */
    onclickWhatsAppChat;
    /** @type {() => number} */
    projectSharingIdFn;
    /** @type {import("@odoo/owl").Signal<HTMLElement>} */
    quickActionsRef;
    /** @type {() => void} */
    sendMessage;
    /** @type {() => boolean} */
    showFullComposerFn;
    /** @type {() => string} */
    typeFn;
    /** @type {() => Object} */
    voiceRecorderFn;
    /** @type {() => Object} */
    voiceTranscriptionFn;

    /**
     * @param {Object} param0
     * @param {(value: any, postData?: Object, extraData?: Object) => Promise<void>} [param0._sendMessage]
     * @param {() => boolean} [param0.active]
     * @param {(emoji: string) => void} [param0.addEmoji]
     * @param {() => boolean} [param0.allowUpload]
     * @param {() => boolean} [param0.areAllActionsDisabled]
     * @param {Composer|() => Composer} param0.composer
     * @param {import("@odoo/owl").Signal<HTMLElement>} [param0.extraActionsRef]
     * @param {import("@odoo/owl").Signal<HTMLButtonElement>} [param0.fileUploaderRef]
     * @param {boolean} [param0.inChatter]
     * @param {boolean} [param0.inDiscussApp]
     * @param {boolean} [param0.inFrontendPortalChatter]
     * @param {boolean} [param0.inKnowledge]
     * @param {() => boolean} [param0.isFullComposerOpen]
     * @param {() => boolean} [param0.isSendButtonDisabled]
     * @param {import("@odoo/owl").Signal<HTMLElement>} [param0.moreActionsRef]
     * @param {() => void} [param0.onClickFullComposer]
     * @param {(ev: Event) => void} [param0.onClickInsertCannedResponse]
     * @param {() => void} [param0.onclickWhatsAppChat]
     * @param {() => number} [param0.projectSharingId]
     * @param {import("@odoo/owl").Signal<HTMLElement>} [param0.quickActionsRef]
     * @param {() => void} [param0.sendMessage]
     * @param {() => boolean} [param0.showFullComposer]
     * @param {() => string} [param0.type]
     * @param {() => Object} [param0.voiceRecorder]
     * @param {() => Object} [param0.voiceTranscription]
     */
    constructor({
        _sendMessage,
        active,
        addEmoji,
        allowUpload,
        areAllActionsDisabled,
        composer,
        extraActionsRef,
        fileUploaderRef,
        inChatter,
        inDiscussApp,
        inFrontendPortalChatter,
        inKnowledge,
        isFullComposerOpen,
        isSendButtonDisabled,
        moreActionsRef,
        onClickFullComposer,
        onClickInsertCannedResponse,
        onclickWhatsAppChat,
        projectSharingId,
        quickActionsRef,
        sendMessage,
        showFullComposer,
        type,
        voiceRecorder,
        voiceTranscription,
    }) {
        super(...arguments);
        this._sendMessage = _sendMessage;
        this.activeFn = active;
        this.addEmoji = addEmoji;
        this.allowUploadFn = allowUpload;
        this.areAllActionsDisabledFn = areAllActionsDisabled;
        this.composerFn = typeof composer === "function" ? composer : () => composer;
        this.extraActionsRef = extraActionsRef;
        this.fileUploaderRef = fileUploaderRef;
        this.inChatter = inChatter;
        this.inDiscussApp = inDiscussApp;
        this.inFrontendPortalChatter = inFrontendPortalChatter;
        this.inKnowledge = inKnowledge;
        this.isFullComposerOpenFn = isFullComposerOpen;
        this.isSendButtonDisabledFn = isSendButtonDisabled;
        this.moreActionsRef = moreActionsRef;
        this.onClickFullComposer = onClickFullComposer;
        this.onClickInsertCannedResponse = onClickInsertCannedResponse;
        this.onclickWhatsAppChat = onclickWhatsAppChat;
        this.projectSharingIdFn = projectSharingId;
        this.quickActionsRef = quickActionsRef;
        this.sendMessage = sendMessage;
        this.showFullComposerFn = showFullComposer;
        this.typeFn = type;
        this.voiceRecorderFn = voiceRecorder;
        this.voiceTranscriptionFn = voiceTranscription;
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
            _sendMessage: this._sendMessage,
            active: this.activeFn?.(),
            addEmoji: this.addEmoji,
            allowUpload: this.allowUploadFn?.(),
            areAllActionsDisabled: this.areAllActionsDisabledFn?.(),
            composer: this.composerFn(),
            extraActionsRef: this.extraActionsRef,
            fileUploaderRef: this.fileUploaderRef,
            inChatter: this.inChatter,
            inDiscussApp: this.inDiscussApp,
            inFrontendPortalChatter: this.inFrontendPortalChatter,
            inKnowledge: this.inKnowledge,
            isFullComposerOpen: this.isFullComposerOpenFn?.(),
            isSendButtonDisabled: this.isSendButtonDisabledFn?.(),
            moreActionsRef: this.moreActionsRef,
            onClickFullComposer: this.onClickFullComposer,
            onClickInsertCannedResponse: this.onClickInsertCannedResponse,
            onclickWhatsAppChat: this.onclickWhatsAppChat,
            projectSharingId: this.projectSharingIdFn?.(),
            quickActionsRef: this.quickActionsRef,
            sendMessage: this.sendMessage,
            showFullComposer: this.showFullComposerFn?.(),
            type: this.typeFn?.(),
            voiceRecorder: this.voiceRecorderFn?.(),
            voiceTranscription: this.voiceTranscriptionFn?.(),
        });
    }
}

/** @typedef {UseActions<ComposerActionParams, ComposerAction>} UseComposerActions_Def */
class UseComposerActions extends UseActions {
    ActionClass = ComposerAction;
}

/**
 * @param {import("@mail/core/common/action").ActionRootRefParam & ComposerActionSpecificParams} [params0={}]
 * @returns {UseComposerActions_Def}
 */
export function useComposerActions({
    _sendMessage,
    active,
    addEmoji,
    allowUpload,
    areAllActionsDisabled,
    composer,
    extraActionsRef,
    fileUploaderRef,
    inChatter,
    inDiscussApp,
    inFrontendPortalChatter,
    inKnowledge,
    isFullComposerOpen,
    isSendButtonDisabled,
    moreActionsRef,
    onClickFullComposer,
    onClickInsertCannedResponse,
    onclickWhatsAppChat,
    projectSharingId,
    quickActionsRef,
    rootRef,
    sendMessage,
    showFullComposer,
    type,
    voiceRecorder,
    voiceTranscription,
} = {}) {
    return useAction(composerActionsRegistry, UseComposerActions, ComposerAction, {
        _sendMessage,
        active,
        addEmoji,
        allowUpload,
        areAllActionsDisabled,
        composer,
        extraActionsRef,
        fileUploaderRef,
        inChatter,
        inDiscussApp,
        inFrontendPortalChatter,
        inKnowledge,
        isFullComposerOpen,
        isSendButtonDisabled,
        moreActionsRef,
        onClickFullComposer,
        onClickInsertCannedResponse,
        onclickWhatsAppChat,
        projectSharingId,
        quickActionsRef,
        rootRef,
        sendMessage,
        showFullComposer,
        type,
        voiceRecorder,
        voiceTranscription,
    });
}
