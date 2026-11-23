import { CreatePollDialog } from "@mail/core/common/create_poll_dialog";

import { EmojiPicker, useEmojiPickerStoreScroll } from "@web/core/emoji_picker/emoji_picker";

import {
    Action,
    ACTION_TAGS,
    IS_ACTION_GROUP_DESCRIPTION_SYM,
    IS_ACTION_DEFINITION_SYM,
    useAction,
    UseActions,
} from "@mail/core/common/action";
import { CannedResponseSuggestionPlugin } from "@mail/core/common/plugin/suggestion/canned_response_suggestion_plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const composerActionsRegistry = registry.category("mail.composer/actions");

/** @typedef {import("models").Composer} Composer */
/**
 * Params the composer gives to its actions. Modules add more by patching
 * `Composer.composerActionsParams`. A param must not reuse a key of `Action.params` (e.g.
 * `action`, `store`), as it would replace it. A value that can change, or is only set after
 * `setup`, is given as a function so that actions always read its current value.
 *
 * @typedef {Object} ComposerActionComponentParams
 * @property {(emoji: string) => void} addEmoji
 * @property {() => boolean} allowUpload
 * @property {() => boolean} areAllActionsDisabled
 * @property {() => "message"|"note"|false|undefined} composerType
 * @property {import("@odoo/owl").Signal<HTMLButtonElement>} fileUploaderRef
 * @property {(ev: MouseEvent) => void} insertCannedResponse
 * @property {() => boolean} isFullComposerOpen
 * @property {() => boolean} isSendButtonDisabled
 * @property {() => void} openFullComposer
 * @property {(body: string, postData?: Object) => Promise} postMessage posts `body` instead of
 *   the content of the composer, e.g. a GIF
 * @property {() => import("@html_editor/editor").Editor|undefined} readyEditor once attached
 * @property {() => Promise} sendMessage
 * @property {() => boolean} showFullComposer
 */
/** @typedef {{composer: Composer} & ComposerActionComponentParams} ComposerActionSpecificParams */
/** @typedef {import("@mail/core/common/action").ActionParams<ComposerAction, UseComposerActions_Def> & ComposerActionSpecificParams} ComposerActionParams */
/** @typedef {import("@mail/core/common/action").ActionDefinition<ComposerActionParams, ComposerAction>} ComposerActionDefinition */

/**
 * @param {string} id
 * @param {ComposerActionDefinition} definition
 */
export function registerComposerAction(id, definition) {
    composerActionsRegistry.add(
        id,
        Object.assign(definition, { [IS_ACTION_DEFINITION_SYM]: true })
    );
}

export function describeComposerActionGroup(id, definition) {
    composerActionsRegistry.add(
        id,
        Object.assign(definition, { [IS_ACTION_GROUP_DESCRIPTION_SYM]: true })
    );
}

registerComposerAction("send-message", {
    condition: ({ ancestors, composer, store }) =>
        (store.ui.isSmall() && composer.message) || (!ancestors.inChatter && !composer.message),
    disabledCondition: ({ isSendButtonDisabled }) => isSendButtonDisabled(),
    hasBtnBg: true,
    icon: "send",
    isActive: ({ isSendButtonDisabled }) => !isSendButtonDisabled(),
    name: ({ composer, composerType }) =>
        composer.message
            ? _t("Save editing")
            : composer.targetThread?.channel
            ? _t("Send")
            : composerType() === "note"
            ? _t("Log")
            : _t("Send"),
    onSelected: ({ sendMessage }) => sendMessage(),
    sequenceQuick: 30,
    tags: ({ action }) => (action.isActive ? ACTION_TAGS.PRIMARY : undefined),
});
registerComposerAction("add-emoji", {
    disabledCondition: ({ areAllActionsDisabled }) => areAllActionsDisabled(),
    icon: "sentiment_satisfied",
    name: _t("Add Emojis"),
    panel: {
        component: EmojiPicker,
        name: _t("Emoji"),
        props: ({ action, addEmoji }) => ({
            onSelect: (emoji) => addEmoji(emoji),
            onClose: () => action.closePanel(),
            storeScroll: action.emojiStoreScroll,
        }),
    },
    setup({ store }) {
        if (!store.ui.isSmall()) {
            this.emojiStoreScroll = useEmojiPickerStoreScroll();
        }
    },
    sequenceQuick: 20,
});
registerComposerAction("upload-files", {
    disabledCondition: ({ areAllActionsDisabled }) => areAllActionsDisabled(),
    condition: ({ allowUpload }) => allowUpload(),
    icon: "attach_file",
    name: _t("Attach Files"),
    onSelected: ({ composer, fileUploaderRef }) => {
        fileUploaderRef()?.click();
        composer.autofocus++;
    },
    sequence: 20,
});
registerComposerAction("open-full-composer", {
    condition: ({ ancestors, composer, showFullComposer }) =>
        showFullComposer() &&
        composer.targetThread &&
        !composer.targetThread.channel &&
        !ancestors.inFrontendPortalChatter,
    hasBtnBg: ({ composer, isFullComposerOpen }) =>
        (composer.restoredFromFullComposer && !isFullComposerOpen()) || undefined,
    hotkey: "shift+c",
    icon: "expand_content",
    isActive: ({ composer, isFullComposerOpen }) =>
        (composer.restoredFromFullComposer && !isFullComposerOpen()) || undefined,
    name: ({ composer }) =>
        composer.message ? _t("Edit in Full Composer") : _t("Open Full Composer"),
    onSelected: ({ openFullComposer }) => openFullComposer(),
    sequence: 30,
    tags: ({ composer, isFullComposerOpen }) =>
        composer.restoredFromFullComposer && !isFullComposerOpen()
            ? [ACTION_TAGS.PRIMARY]
            : undefined,
});
registerComposerAction("add-canned-response", {
    condition: ({ composer, readyEditor, store }) =>
        store.hasCannedResponses &&
        composer.targetThread &&
        Boolean(readyEditor()?.shared[CannedResponseSuggestionPlugin.id]),
    icon: "article",
    name: _t("Insert Canned Response"),
    onSelected: ({ insertCannedResponse }, ev) => insertCannedResponse(ev),
    sequence: 5,
});
registerComposerAction("create-poll", {
    name: _t("Create Poll"),
    icon: "oi_view-cohort",
    condition: ({ composer, store }) => {
        if (!store.self_user || store.self_user.share || composer.message) {
            return false;
        }
        return ["channel", "group"].includes(composer.targetThread?.channel?.channel_type);
    },
    onSelected: ({ action, composer }) => {
        action.dialogService.add(
            CreatePollDialog,
            { thread: composer.targetThread },
            { rootRef: action.actionRef }
        );
    },
    setup: ({ action }) => {
        action.dialogService = useService("dialog");
    },
});

export class ComposerAction extends Action {
    /** @type {() => Composer} */
    composerFn;
    /** @type {ComposerActionComponentParams} */
    componentParams;

    /**
     * @param {Object} param0
     * @param {Composer|() => Composer} param0.composer
     * @param {ComposerActionComponentParams} [param0.componentParams]
     */
    constructor({ composer, componentParams }) {
        super(...arguments);
        this.composerFn = typeof composer === "function" ? composer : () => composer;
        this.componentParams = componentParams ?? {};
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
        return Object.assign(super.params, this.componentParams, { composer: this.composerFn() });
    }
}

/** @typedef {UseActions<ComposerActionParams, ComposerAction>} UseComposerActions_Def */
class UseComposerActions extends UseActions {
    ActionClass = ComposerAction;

    /** Takes the same flat params as `useComposerActions`, which the composer gives to both. */
    more({ composer, rootRef, ...componentParams } = {}, data, id) {
        return super.more({ composer, componentParams, rootRef }, data, id);
    }
}

/**
 * @param {import("@mail/core/common/action").ActionRootRefParam & {composer?: Composer|() => Composer} & ComposerActionComponentParams} params0
 * @returns {UseComposerActions_Def}
 */
export function useComposerActions({ composer, rootRef, ...componentParams } = {}) {
    return useAction(composerActionsRegistry, UseComposerActions, ComposerAction, {
        componentParams,
        composer,
        rootRef,
    });
}
