// @ts-check
/** @odoo-module native */
import { closestElement, lastLeaf } from "@html_editor/utils/dom_traversal";
import { rightPos } from "@html_editor/utils/position";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { ActionList } from "@mail/core/common/action_list";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { useComposerActions } from "@mail/core/common/composer_actions";
import {
    clearComposerDraft,
    restoreComposerDraft,
    saveComposerDraft,
    useComposerDraft,
} from "@mail/core/common/composer_draft";
import { useFullComposer } from "@mail/core/common/full_composer_hook";
import { MailAttachmentDropzone } from "@mail/core/common/mail_attachment_dropzone";
import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";
import { NavigableList } from "@mail/core/common/navigable_list";
import {
    MAIL_PLUGINS,
    MAIL_SMALL_UI_PLUGINS,
} from "@mail/core/common/plugin/plugin_sets";
import {
    mapSuggestionsToOptions,
    useSuggestion,
} from "@mail/core/common/suggestion_hook";
import { insertAtSelection } from "@mail/utils/common/composer_insert";
import { trimEmptyBlocksAround } from "@mail/utils/common/format";
import { useSelection } from "@mail/utils/common/hooks";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";
import { markThreadAsReadIfAtBottom } from "@mail/utils/common/thread_read";
import {
    Component,
    markup,
    onMounted,
    onWillUnmount,
    reactive,
    status,
    toRaw,
    useChildSubEnv,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { Dropdown, DropdownItem } from "@web/components/dropdown";
import { useCustomDropzone } from "@web/components/dropzone";
import {
    isDisplayStandalone,
    isIOS,
    isMobileOS,
} from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { FileUploader } from "@web/core/file_upload";
import { _t } from "@web/core/translation";
import { delay } from "@web/core/utils/concurrency";
import { isEventHandled, markEventHandled } from "@web/core/utils/dom/events";
import { htmlJoin, isHtmlEmpty, setElementContent } from "@web/core/utils/dom/html";
import { isEmail } from "@web/core/utils/format/strings";
import { useService } from "@web/core/utils/hooks";
import { rootIdOf } from "@web/ui/overlay/root_id";
const EDIT_CLICK_TYPE = {
    CANCEL: "cancel",
    SAVE: "save",
};

const log = makeLogger("mail.composer");

/**
 * @typedef {Object} Props
 * @property {import("models").Composer} composer
 * @property {'compact'|'normal'|'extended'} [mode]
 * @property {'message'|'note'|false} [type]
 * @property {string} [placeholder]
 * @property {string} [className]
 * @property {function} [onDiscardCallback]
 * @property {function} [onPostCallback]
 * @property {number} [autofocus]
 * @property {import("@web/core/utils/hooks").Ref} [dropzoneRef]
 * @property {boolean} [sidebar=true]
 * @property {boolean} [showFullComposer=true]
 * @property {boolean} [allowUpload=true]
 * @property {function} [onCloseFullComposerCallback]
 * @extends {Component<Props, import("@web/env").OdooEnv>}
 */
export class Composer extends Component {
    static components = {
        ActionList,
        AttachmentList,
        Dropdown,
        DropdownItem,
        FileUploader,
        NavigableList,
        Wysiwyg,
    };
    static defaultProps = {
        autofocus: 0,
        mode: "normal",
        className: "",
        sidebar: true,
        showFullComposer: true,
        allowUpload: true,
    };
    static props = [
        "composer",
        "autofocus?",
        "onCloseFullComposerCallback?",
        "onDiscardCallback?",
        "onPostCallback?",
        "mode?",
        "placeholder?",
        "dropzoneRef?",
        "className?",
        "sidebar?",
        "type?",
        "showFullComposer?",
        "allowUpload?",
    ];
    static template = "mail.Composer";

    _setupServices() {
        this.dialogService = useService("dialog");
        /** @type {import("@html_editor/editor").Editor} */
        this.editor = undefined;
        this.isMobileOS = isMobileOS();
        this.isIosPwa = isIOS() && isDisplayStandalone();
        this.store = useService("mail.store");
        this.composerActions = useComposerActions({
            composer: () => this.props.composer,
        });
        this.EDIT_CLICK_TYPE = EDIT_CLICK_TYPE;
        this.OR_PRESS_SEND_KEYBIND = _t("or press %(send_keybind)s", {
            send_keybind: htmlJoin(
                this.sendKeybinds.map((key) => markup`<samp>${key}</samp>`),
                " + ",
            ),
        });
        this.attachmentUploader = useAttachmentUploader(
            this.thread ?? this.props.composer.message.thread,
            { composer: this.props.composer },
        );
        this.ui = useService("ui");
        this.composerService = useService("mail.composer");
        this.ref = useRef("textarea");
        this.fakeTextarea = useRef("fakeTextarea");
        this.inputContainerRef = useRef("input-container");
        this.pickerContainerRef = useRef("picker-container");
        this.state = useState({
            active: true,
        });
        this.root = useRef("root");
        this.fullComposer = useFullComposer();
        this.draft = useComposerDraft();
    }
    _setupSelection() {
        this.selection = useSelection({
            refName: "textarea",
            model: this.props.composer.selection,
            /** @param {MouseEvent} ev */
            preserveOnClickAwayPredicate: async (ev) => {
                await delay();
                return (
                    !this.isEventTrusted(ev) ||
                    isEventHandled(ev, "sidebar.openThread") ||
                    isEventHandled(ev, "emoji.selectEmoji") ||
                    isEventHandled(ev, "Composer.onClickAddEmoji") ||
                    isEventHandled(ev, "composer.clickOnAddAttachment") ||
                    isEventHandled(ev, "composer.selectSuggestion") ||
                    isEventHandled(ev, "composer.clickInsertCannedResponse")
                );
            },
        });
    }
    _setupInputHandlers() {
        this.suggestion = useSuggestion();
        this.markEventHandled = markEventHandled;
        this.onDropFile = this.onDropFile.bind(this);
        this.updateFromEditor = false;
        useExternalListener(
            window,
            "click",
            /** @param {MouseEvent} ev */
            (ev) => {
                const target = ev.composedPath()[0];
                if (
                    this.ui.isSmall &&
                    this.composerActions.activePicker &&
                    this.pickerContainerRef.el &&
                    target !== this.pickerContainerRef.el &&
                    !this.pickerContainerRef.el.contains(/** @type {Node} */ (target))
                ) {
                    this.composerActions.activePicker.close?.();
                }
            },
            { capture: true },
        );
        if (this.props.dropzoneRef) {
            useCustomDropzone(
                this.props.dropzoneRef,
                MailAttachmentDropzone,
                {
                    extraClass: "o-mail-Composer-dropzone",
                    onDrop: this.onDropFile,
                },
                () =>
                    this.props.allowUpload &&
                    (!this.store.rtc.state.isFullscreen || this.env.inMeetingView),
            );
        }
    }
    _setupEffects() {
        useChildSubEnv({ inComposer: true });
        useEffect(
            /** @param {number} focus */
            (focus) => {
                if (focus && this.ref.el) {
                    this.selection.restore();
                    this.ref.el.focus();
                }
                if (focus && this.editor) {
                    this.editor.shared.selection.focusEditable();
                    this.editor.shared.selection.selectAroundNonEditable();
                }
            },
            () => [
                this.props.autofocus,
                this.props.composer.autofocus,
                this.props.placeholder,
            ],
        );
        useEffect(
            () => {
                if (this.props.composer.replyToMessage) {
                    this.props.composer.autofocus++;
                }
            },
            () => [this.props.composer.replyToMessage],
        );
        useEffect(
            () => {
                const fakeTextarea = /** @type {HTMLTextAreaElement|null} */ (
                    this.fakeTextarea.el
                );
                if (fakeTextarea?.scrollHeight) {
                    let wasEmpty = false;
                    if (!fakeTextarea.value) {
                        wasEmpty = true;
                        fakeTextarea.value = "0";
                    }
                    this.ref.el.style.height = fakeTextarea.scrollHeight + "px";
                    if (wasEmpty) {
                        fakeTextarea.value = "";
                    }
                }
            },
            () => [this.props.composer.composerText, this.ref.el],
        );
        useEffect(
            () => {
                if (!this.props.composer.forceCursorMove) {
                    return;
                }
                this.selection.restore();
                this.props.composer.forceCursorMove = false;
            },
            () => [this.props.composer.forceCursorMove],
        );
        onMounted(() => {
            this.ref.el?.scrollTo({ top: 0, behavior: "instant" });
        });
        onWillUnmount(() => {
            this.props.composer.isFocused = false;
            this.editor = undefined;
        });
    }
    _setupComposerSync() {
        const composerProxy = reactive(this.props.composer, () => {
            if (status(this) === "destroyed") {
                return;
            }
            const composerHtml = composerProxy.composerHtml;
            if (this.updateFromEditor) {
                return;
            }
            if (!this.editor?.editable) {
                return;
            }
            log.pipeline("composerSync model -> editor", () => ({
                thread: this.props.composer.thread?.localId,
                length: String(composerHtml).length,
            }));
            setElementContent(this.editor.editable, composerHtml);
            this.setEditorCursorEnd();
            this.editor.shared.history.addStep();
        });
        void composerProxy.composerHtml;
    }
    setup() {
        useLifecycleLog(log);
        super.setup();
        this._setupServices();
        this._setupSelection();
        this._setupInputHandlers();
        this._setupEffects();
        this._setupComposerSync();
    }

    setEditorCursorEnd() {
        const lastNode = lastLeaf(this.editor?.editable);
        if (!lastNode) {
            return;
        }
        const nonEditableAncestor = closestElement(
            lastNode,
            /** @param {HTMLElement} el */ (el) => !el.isContentEditable,
        );
        if (nonEditableAncestor && this.editor.editable.contains(nonEditableAncestor)) {
            const [anchorNode, anchorOffset] = rightPos(nonEditableAncestor);
            this.editor.shared.selection.setSelection({ anchorNode, anchorOffset });
        } else {
            this.editor.shared.selection.setCursorEnd(lastNode);
        }
        this.editor.shared.selection.selectAroundNonEditable();
    }

    get areAllActionsDisabled() {
        return false;
    }

    get isMultiUpload() {
        return true;
    }

    get placeholder() {
        if (this.props.placeholder) {
            return this.props.placeholder;
        }
        if (this.thread) {
            return this.thread.composerPlaceholder;
        }
        return "";
    }

    get wysiwygConfig() {
        return {
            content: this.props.composer.composerHtml,
            placeholder: this.placeholder,
            Plugins: this.ui.isSmall ? MAIL_SMALL_UI_PLUGINS : MAIL_PLUGINS,
            composerPluginDependencies: {
                /**
                 * @param {Selection} selection
                 * @param {ClipboardEvent} ev
                 */
                onBeforePaste: (selection, ev) => this.onPaste(ev),
                onFocusin: this.onFocusin.bind(this),
                onFocusout: this.onFocusout.bind(this),
                onInput: this.onInput.bind(this),
                onKeydown: this.onKeydown.bind(this),
            },
            classList: ["o-mail-Composer-html"],
            onChange: () => this.onChangeWysiwygContent(),
            onEditorReady: () => {
                this.setEditorCursorEnd();
                this.editor.shared.history.addStep();
            },
        };
    }

    /** @param {MouseEvent} ev */
    onClickCancelOrSaveEditText(ev) {
        const composer = toRaw(this.props.composer);
        const target = /** @type {HTMLElement} */ (ev.target);
        if (composer.message && target.dataset?.type === EDIT_CLICK_TYPE.CANCEL) {
            this.props.onDiscardCallback(ev);
        }
        if (composer.message && target.dataset?.type === EDIT_CLICK_TYPE.SAVE) {
            this.editMessage();
        }
    }

    get CANCEL_OR_SAVE_EDIT_TEXT() {
        const tags = {
            open_samp: markup`<samp>`,
            close_samp: markup`</samp>`,
            open_em: markup`<em>`,
            close_em: markup`</em>`,
            open_cancel: markup`<button class="btn btn-link fst-italic p-0 align-baseline" data-type="${EDIT_CLICK_TYPE.CANCEL}">`,
            close_cancel: markup`</button>`,
            open_save: markup`<button class="btn btn-link fst-italic p-0 align-baseline" data-type="${EDIT_CLICK_TYPE.SAVE}">`,
            close_save: markup`</button>`,
        };
        return this.env.inChatter
            ? _t(
                  "%(open_samp)sEscape%(close_samp)s %(open_em)sto %(open_cancel)scancel%(close_cancel)s%(close_em)s, %(open_samp)sCTRL-Enter%(close_samp)s %(open_em)sto %(open_save)ssave%(close_save)s%(close_em)s",
                  tags,
              )
            : _t(
                  "%(open_samp)sEscape%(close_samp)s %(open_em)sto %(open_cancel)scancel%(close_cancel)s%(close_em)s, %(open_samp)sEnter%(close_samp)s %(open_em)sto %(open_save)ssave%(close_save)s%(close_em)s",
                  tags,
              );
    }

    get SEND_TEXT() {
        if (this.props.composer.message) {
            return _t("Save editing");
        }
        return this.props.type === "note" ? _t("Log") : _t("Send");
    }

    get sendKeybinds() {
        return this.env.inChatter ? [_t("CTRL"), _t("Enter")] : [_t("Enter")];
    }

    get showComposerAvatar() {
        return this.props.mode !== "compact" && this.props.sidebar;
    }

    get thread() {
        return this.props.composer.targetThread;
    }

    get allowUpload() {
        return this.props.allowUpload;
    }

    get message() {
        return this.props.composer.message ?? null;
    }

    get extraData() {
        return this.thread.rpcParams;
    }

    get isSendButtonDisabled() {
        const attachments = this.props.composer.attachments;
        return (
            !this.state.active ||
            (isHtmlEmpty(this.props.composer.composerHtml) &&
                attachments.length === 0) ||
            attachments.some(({ uploading }) => Boolean(uploading))
        );
    }

    get hasSuggestions() {
        return Boolean(this.suggestion?.state.items);
    }

    get navigableListProps() {
        const props = {
            anchorRef: this.inputContainerRef.el,
            position: this.env.inChatter ? "bottom-fit" : "top-fit",
            /**
             * @param {Event} ev
             * @param {Object} option
             */
            onSelect: (ev, option) => {
                this.suggestion.insert(option);
                markEventHandled(ev, "composer.selectSuggestion");
            },
            isLoading:
                !!this.suggestion.search.term && this.suggestion.state.isFetching,
            /** @type {Object[]} */
            options: [],
        };
        if (!this.hasSuggestions) {
            return props;
        }
        return {
            ...props,
            ...mapSuggestionsToOptions(
                this.suggestion.state.items.type,
                this.suggestion.state.items.suggestions,
                { thread: this.thread },
            ),
        };
    }

    /** @param {DragEvent} ev */
    onDropFile(ev) {
        if (isDragSourceExternalFile(ev.dataTransfer)) {
            log.logic("onDropFile", () => ({ files: ev.dataTransfer.files.length }));
            for (const file of ev.dataTransfer.files) {
                this.attachmentUploader.uploadFile(file);
            }
        }
    }

    /** @param {boolean} isDiscard */
    onCloseFullComposerCallback(isDiscard) {
        log.lifecycle("fullComposer closed", () => ({
            thread: this.thread?.localId,
            isDiscard,
            delegated: Boolean(this.props.onCloseFullComposerCallback),
        }));
        if (this.props.onCloseFullComposerCallback) {
            this.props.onCloseFullComposerCallback(isDiscard);
        } else {
            this.thread?.fetchNewMessages();
        }
    }

    /** @param {InputEvent} ev */
    onInput(ev) {
        if (!this.props.composer.isDirty) {
            this.props.composer.isDirty = true;
        }
    }

    /** @param {ClipboardEvent} ev */
    onPaste(ev) {
        if (!this.allowUpload) {
            return;
        }
        if (!ev.clipboardData?.items) {
            return;
        }
        if (ev.clipboardData.files.length === 0) {
            return;
        }
        ev.preventDefault();
        log.logic("onPaste files", () => ({ files: ev.clipboardData.files.length }));
        for (const file of ev.clipboardData.files) {
            this.attachmentUploader.uploadFile(file);
        }
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        const composer = toRaw(this.props.composer);
        switch (ev.key) {
            case "ArrowUp":
                if (
                    !this.env.inChatter &&
                    composer.composerText === "" &&
                    composer.thread
                ) {
                    const messageToEdit = composer.thread.lastEditableMessageOfSelf;
                    log.logic("ArrowUp edit last message", () => ({
                        thread: composer.thread.localId,
                        messageId: messageToEdit?.id,
                    }));
                    if (messageToEdit) {
                        messageToEdit.enterEditMode(this.props.composer.thread);
                    }
                }
                break;
            case "Enter": {
                if (isEventHandled(ev, "NavigableList.select") || !this.state.active) {
                    ev.preventDefault();
                    return;
                }
                if (this.isMobileOS || ev.isComposing) {
                    return;
                }
                const shouldPost = this.env.inChatter ? ev.ctrlKey : !ev.shiftKey;
                log.logic("Enter", () => ({
                    thread: composer.thread?.localId,
                    shouldPost,
                    inChatter: this.env.inChatter,
                    editing: Boolean(composer.message),
                }));
                if (!shouldPost) {
                    return;
                }
                ev.preventDefault();
                if (composer.message) {
                    this.editMessage();
                } else {
                    this.sendMessage();
                }
                break;
            }
            case "Escape":
                if (isEventHandled(ev, "NavigableList.close")) {
                    return;
                }
                if (this.props.onDiscardCallback) {
                    log.logic("Escape discard", () => ({
                        thread: composer.thread?.localId,
                    }));
                    this.props.onDiscardCallback();
                    markEventHandled(ev, "Composer.discard");
                }
                break;
        }
    }

    get fullComposerAdditionalContext() {
        return {};
    }

    async onClickFullComposer() {
        log.logic("onClickFullComposer", () => ({ thread: this.thread?.localId }));
        await this.fullComposer.open();
    }

    /**
     * @param {string|ReturnType<markup>} defaultBody
     * @param {string|ReturnType<markup>} [signature=""]
     * @returns {ReturnType<markup>}
     */
    formatDefaultBodyForFullComposer(defaultBody, signature = "") {
        if (signature) {
            defaultBody = markup`${defaultBody}<br>${signature}`;
        }
        return markup`<div>${defaultBody}</div>`;
    }

    clear() {
        this.props.composer.clear();
        clearComposerDraft(this.props.composer);
    }

    notifySendFromMailbox() {
        this.store.notifySendFromMailbox(this.thread.displayName);
    }

    /**
     * @param {Event} ev
     * @returns {boolean}
     */
    isEventTrusted(ev) {
        return ev.isTrusted;
    }

    /** @param {(value: ReturnType<markup>|string) => Promise<void>} cb */
    async processMessage(cb) {
        log.logic("processMessage", () => ({
            thread: this.props.composer.thread?.localId,
            canProcess: this.canProcessMessage,
            active: this.state.active,
            attachments: this.props.composer.attachments.length,
        }));
        if (this.props.composer.attachments.some(({ uploading }) => uploading)) {
            log.logic("processMessage blocked by upload in progress");
            this.env.services.notification.add(
                _t("Please wait while the file is uploading."),
                {
                    type: "warning",
                },
            );
        } else if (this.canProcessMessage) {
            if (!this.state.active) {
                log.logic("processMessage already in flight");
                return;
            }
            this.state.active = false;
            const endProcess = log.perf("processMessage");
            try {
                await cb(trimEmptyBlocksAround(this.props.composer.composerHtml));
                if (this.props.onPostCallback) {
                    this.props.onPostCallback();
                }
                this.clear();
                this.ref.el?.focus();
                endProcess({ thread: this.props.composer.thread?.localId });
            } catch (error) {
                endProcess({
                    thread: this.props.composer.thread?.localId,
                    failed: true,
                });
                throw error;
            } finally {
                this.state.active = true;
            }
        }
    }

    get canProcessMessage() {
        return (
            !isHtmlEmpty(this.props.composer.composerHtml) ||
            this.props.composer.attachments.length > 0 ||
            (this.message && this.message.attachment_ids.length > 0)
        );
    }

    async sendMessage() {
        const composer = toRaw(this.props.composer);
        log.logic("sendMessage", () => ({
            thread: composer.thread?.localId,
            type: this.props.type,
            editing: Boolean(composer.message),
        }));
        this.composerActions.activePicker?.close?.();
        if (composer.message) {
            this.editMessage();
            return;
        }
        if (this.props.type !== "note") {
            const allRecipients = composer.thread.allRecipients;
            if (
                allRecipients.some(
                    (recipient) => !recipient.email || !isEmail(recipient.email),
                )
            ) {
                log.logic("sendMessage refused: invalid recipient email", () => ({
                    thread: composer.thread?.localId,
                    recipients: allRecipients.length,
                }));
                this.env.services.notification.add(
                    _t(
                        "Cannot send: a recipient has a missing or invalid email address.",
                    ),
                    { type: "danger" },
                );
                return;
            }
        }
        await this.processMessage(
            /** @param {ReturnType<markup>|string} value */ async (value) => {
                await this._sendMessage(value, this.postData, this.extraData);
            },
        );
    }

    get postData() {
        const composer = toRaw(this.props.composer);
        return {
            attachments: composer.attachments || [],
            emailAddSignature: composer.emailAddSignature,
            isNote: this.props.type === "note",
            mentionedChannels: composer.mentionedChannels || [],
            mentionedPartners: composer.mentionedPartners || [],
            mentionedRoles: composer.mentionedRoles || [],
            cannedResponseIds: composer.cannedResponses.map((c) => c.id),
            parentId: this.props.composer.replyToMessage?.id,
        };
    }

    /**
     * @typedef postData
     * @property {import("models").Attachment[]} attachments
     * @property {boolean} emailAddSignature
     * @property {boolean} isNote
     * @property {number | string} parentId
     * @property {import("models").Thread[]} mentionedChannels
     * @property {import("models").ResPartner[]} mentionedPartners
     * @property {import("models").ResRole[]} mentionedRoles
     * @property {number[]} cannedResponseIds
     */
    /**
     * @param {ReturnType<markup> | string} value
     * @param {Partial<postData>} postData
     * @param {Object} extraData
     */
    async _sendMessage(value, postData, extraData) {
        const thread = toRaw(this.props.composer.thread);
        const postThread = toRaw(this.thread);
        const post = postThread.post.bind(postThread, value, postData, extraData);
        let message;
        log.pipeline("_sendMessage", () => ({
            thread: thread?.localId,
            postThread: postThread.localId,
            optimistic: postThread.hasOptimisticPost,
            attachments: postData.attachments?.length,
            isMailbox: thread.isMailbox,
        }));
        if (postThread.hasOptimisticPost) {
            post();
        } else {
            message = await post();
        }
        if (thread.isMailbox) {
            this.notifySendFromMailbox();
        }
        this.suggestion?.clearRawMentions();
        this.suggestion?.clearCannedResponses();
        this.props.composer.replyToMessage = undefined;
        this.props.composer.emailAddSignature = true;
        this.props.composer.thread.additionalRecipients = [];
        return message;
    }

    async editMessage() {
        const composer = toRaw(this.props.composer);
        log.logic("editMessage", () => ({
            messageId: composer.message?.id,
            askDelete: this.askDeleteFromEdit,
        }));
        if (!this.askDeleteFromEdit) {
            await this.processMessage(
                /** @param {ReturnType<markup>|string} value */ async (value) =>
                    composer.message.edit(value, composer.attachments, {
                        mentionedChannels: composer.mentionedChannels,
                        mentionedPartners: composer.mentionedPartners,
                        mentionedRoles: composer.mentionedRoles,
                    }),
            );
        } else {
            this.env.services.dialog.add(
                MessageConfirmDialog,
                {
                    message: composer.message,
                    onConfirm: () =>
                        this.message.remove({
                            removeFromThread: this.shouldHideFromMessageListOnDelete,
                        }),
                    prompt: _t(
                        "Are you sure you want to bid farewell to this message forever?",
                    ),
                },
                { rootId: rootIdOf(this.root.el) },
            );
        }
        this.suggestion?.clearRawMentions();
    }

    get askDeleteFromEdit() {
        const composer = toRaw(this.props.composer);
        return !composer.composerText && composer.message.attachment_ids.length === 0;
    }

    /** @param {MouseEvent} ev */
    onClickInsertCannedResponse(ev) {
        markEventHandled(ev, "composer.clickInsertCannedResponse");
        const composer = toRaw(this.props.composer);
        let toInsert = "::";
        if (this.editor) {
            if (!isHtmlEmpty(this.props.composer.composerHtml)) {
                this.editor.shared.dom.insert(" ");
            }
        } else {
            const firstPart = composer.composerText.slice(0, composer.selection.start);
            if (firstPart.length !== 0 && firstPart.at(-1) !== " ") {
                toInsert = " ::";
            }
        }
        insertAtSelection(composer, toInsert, {
            editor: this.editor,
            /** @param {number} position */
            moveCursor: (position) => this.selection.moveCursor(position),
        });
        if (!this.ui.isSmall || !this.env.inChatter) {
            composer.autofocus++;
        }
    }

    onChangeWysiwygContent() {
        this.updateFromEditor = true;
        this.props.composer.composerHtml = markup(this.editor.getContent());
        if (!this.props.composer.isDirty) {
            this.props.composer.isDirty = true;
        }
        this.updateFromEditor = false;
    }

    /** @param {import("@html_editor/editor").Editor} editor */
    onLoadWysiwyg(editor) {
        log.lifecycle("wysiwyg loaded", () => ({ thread: this.thread?.localId }));
        this.editor = editor;
    }

    /**
     * @param {string} str
     * @returns {boolean|undefined}
     */
    addEmoji(str) {
        const composer = toRaw(this.props.composer);
        insertAtSelection(composer, str, {
            editor: this.editor,
            /** @param {number} position */
            moveCursor: (position) => this.selection.moveCursor(position),
        });
        if (this.ui.isSmall && !this.env.inChatter) {
            return false;
        } else {
            composer.autofocus++;
        }
    }

    /** @param {FocusEvent} ev */
    onFocusin(ev) {
        ev.stopPropagation();
        const composer = toRaw(this.props.composer);
        composer.isFocused = true;
        if (composer.thread) {
            markThreadAsReadIfAtBottom(composer.thread);
        }
    }

    /** @param {FocusEvent} ev */
    onFocusout(ev) {
        if (
            [EDIT_CLICK_TYPE.CANCEL, EDIT_CLICK_TYPE.SAVE].includes(
                /** @type {HTMLElement|null} */ (ev.relatedTarget)?.dataset?.type,
            )
        ) {
            return;
        }
        this.props.composer.isFocused = false;
    }

    saveContent() {
        const composer = toRaw(this.props.composer);
        if (composer.restoredFromFullComposer && !this.fullComposer.isOpen) {
            log.logic("saveContent skipped: restored from full composer");
            return;
        }
        log.logic("saveContent", () => ({
            thread: composer.thread?.localId,
            fullComposer: this.fullComposer.isOpen,
        }));
        if (this.fullComposer.isOpen) {
            this.fullComposer.saveContent();
        } else {
            saveComposerDraft(composer, {
                composerHtml: composer.composerHtml,
                emailAddSignature: true,
                replyToMessageId: composer.replyToMessage?.id,
                fromFullComposer: false,
            });
        }
    }

    restoreContent() {
        restoreComposerDraft(toRaw(this.props.composer));
    }

    get shouldHideFromMessageListOnDelete() {
        return false;
    }
}
