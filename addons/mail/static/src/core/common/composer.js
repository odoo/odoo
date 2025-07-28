import { AttachmentList } from "@mail/core/common/attachment_list";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { MailAttachmentDropzone } from "@mail/core/common/mail_attachment_dropzone";
import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";
import { NavigableList } from "@mail/core/common/navigable_list";
import { useSuggestion } from "@mail/core/common/suggestion_hook";
import { prettifyMessageContent } from "@mail/utils/common/format";
import { createDocumentFragmentFromContent, htmlJoin } from "@mail/utils/common/html";
import { useSelection } from "@mail/utils/common/hooks";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";
import { rpc } from "@web/core/network/rpc";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";
import { browser } from "@web/core/browser/browser";
import { useDebounced } from "@web/core/utils/timing";

import {
    Component,
    markup,
    onMounted,
    onWillUnmount,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
    useExternalListener,
    toRaw,
    EventBus,
} from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { escape, isEmail } from "@web/core/utils/strings";
import { isDisplayStandalone, isIOS, isMobileOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useComposerActions } from "./composer_actions";

const EDIT_CLICK_TYPE = {
    CANCEL: "cancel",
    SAVE: "save",
};

/**
 * @typedef {Object} Props
 * @property {import("models").Composer} composer
 * @property {import("@mail/utils/common/hooks").MessageToReplyTo} messageToReplyTo
 * @property {import("@mail/utils/common/hooks").MessageEdition} [messageEdition]
 * @property {'compact'|'normal'|'extended'} [mode] default: 'normal'
 * @property {'message'|'note'|false} [type] default: false
 * @property {string} [placeholder]
 * @property {string} [className]
 * @property {function} [onDiscardCallback]
 * @property {function} [onPostCallback]
 * @property {number} [autofocus]
 * @property {import("@web/core/utils/hooks").Ref} [dropzoneRef]
 * @extends {Component<Props, Env>}
 */
export class Composer extends Component {
    static components = {
        AttachmentList,
        Dropdown,
        DropdownItem,
        FileUploader,
        NavigableList,
    };
    static defaultProps = {
        mode: "normal",
        className: "",
        sidebar: true,
        showFullComposer: true,
        allowUpload: true,
    };
    static props = [
        "composer",
        "autofocus?",
        "messageToReplyTo?",
        "onCloseFullComposerCallback?",
        "onDiscardCallback?",
        "onPostCallback?",
        "mode?",
        "placeholder?",
        "dropzoneRef?",
        "messageEdition?",
        "className?",
        "sidebar?",
        "type?",
        "showFullComposer?",
        "allowUpload?",
    ];
    static template = "mail.Composer";

    setup() {
        super.setup();
        this.isMobileOS = isMobileOS();
        this.isIosPwa = isIOS() && isDisplayStandalone();
        this.composerActions = useComposerActions();
        this.OR_PRESS_SEND_KEYBIND = _t("or press %(send_keybind)s", {
            send_keybind: markup(
                this.sendKeybinds.map((key) => `<samp>${escape(key)}</samp>`).join(" + ")
            ),
        });
        this.store = useService("mail.store");
        this.attachmentUploader = useAttachmentUploader(
            this.thread ?? this.props.composer.message.thread,
            { composer: this.props.composer }
        );
        this.ui = useService("ui");
        this.ref = useRef("textarea");
        this.fakeTextarea = useRef("fakeTextarea");
        this.inputContainerRef = useRef("input-container");
        this.pickerContainerRef = useRef("picker-container");
        this.state = useState({
            active: true,
            isFullComposerOpen: false,
        });
        this.fullComposerBus = new EventBus();
        this.selection = useSelection({
            refName: "textarea",
            model: this.props.composer.selection,
            preserveOnClickAwayPredicate: async (ev) => {
                // Let event be handled by bubbling handlers first.
                await new Promise(setTimeout);
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
        this.suggestion = useSuggestion();
        this.markEventHandled = markEventHandled;
        this.onDropFile = this.onDropFile.bind(this);
        this.saveContentDebounced = useDebounced(this.saveContent, 5000, {
            execBeforeUnmount: true,
        });
        useExternalListener(window, "beforeunload", this.saveContent.bind(this));
        useExternalListener(
            window,
            "click",
            (ev) => {
                if (
                    this.ui.isSmall &&
                    this.composerActions.activePicker &&
                    this.pickerContainerRef.el &&
                    ev.target !== this.pickerContainerRef.el &&
                    !this.pickerContainerRef.el.contains(ev.target)
                ) {
                    this.composerActions.activePicker.close?.();
                }
            },
            { capture: true }
        );
        if (this.props.dropzoneRef) {
            useCustomDropzone(
                this.props.dropzoneRef,
                MailAttachmentDropzone,
                {
                    extraClass: "o-mail-Composer-dropzone",
                    onDrop: this.onDropFile,
                },
                () => this.props.allowUpload
            );
        }
        if (this.props.messageEdition) {
            this.props.messageEdition.composerOfThread = this;
        }
        useChildSubEnv({ inComposer: true });
        useEffect(
            (focus) => {
                if (focus && this.ref.el) {
                    this.selection.restore();
                    this.ref.el.focus();
                }
            },
            () => [this.props.autofocus + this.props.composer.autofocus, this.props.placeholder]
        );
        useEffect(
            (rThread, cThread) => {
                if (cThread && cThread.eq(rThread)) {
                    this.props.composer.autofocus++;
                }
            },
            () => [this.props.messageToReplyTo?.thread, this.props.composer.thread]
        );
        useEffect(
            () => {
                if (this.fakeTextarea.el.scrollHeight) {
                    let wasEmpty = false;
                    if (!this.fakeTextarea.el.value) {
                        wasEmpty = true;
                        this.fakeTextarea.el.value = "0";
                    }
                    this.ref.el.style.height = this.fakeTextarea.el.scrollHeight + "px";
                    if (wasEmpty) {
                        this.fakeTextarea.el.value = "";
                    }
                }
                this.saveContentDebounced();
            },
            () => [this.props.composer.text, this.ref.el]
        );
        useEffect(
            () => {
                if (!this.props.composer.forceCursorMove) {
                    return;
                }
                this.selection.restore();
                this.props.composer.forceCursorMove = false;
            },
            () => [this.props.composer.forceCursorMove]
        );
        onMounted(() => {
            this.ref.el.scrollTo({ top: 0, behavior: "instant" });
            if (!this.props.composer.text) {
                this.restoreContent();
            }
        });
        onWillUnmount(() => {
            this.props.composer.isFocused = false;
        });
        useEffect(
            (composerThread, replyToThread) => {
                if (replyToThread && replyToThread !== composerThread) {
                    this.props.messageToReplyTo.cancel();
                }
            },
            () => [this.props.composer.thread, this.props.messageToReplyTo?.thread]
        );
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
            if (this.thread.channel_type === "channel") {
                const threadName = this.thread.displayName;
                if (this.thread.parent_channel_id) {
                    return _t(`Message "%(subChannelName)s"`, {
                        subChannelName: threadName,
                    });
                }
                return _t("Message #%(threadName)s…", { threadName });
            }
            return _t("Message %(thread name)s…", { "thread name": this.thread.displayName });
        }
        return "";
    }

    onClickCancelOrSaveEditText(ev) {
        ev.preventDefault();
        const composer = toRaw(this.props.composer);
        if (composer.message && ev.target.dataset?.type === EDIT_CLICK_TYPE.CANCEL) {
            this.props.onDiscardCallback(ev);
        }
        if (composer.message && ev.target.dataset?.type === EDIT_CLICK_TYPE.SAVE) {
            this.editMessage(ev);
        }
    }

    get CANCEL_OR_SAVE_EDIT_TEXT() {
        if (this.ui.isSmall) {
            return _t(
                "%(open_button)s%(icon)s%(open_em)sDiscard editing%(close_em)s%(close_button)s",
                {
                    open_button: markup(
                        `<button class='btn px-1 py-0' data-type="${escape(
                            EDIT_CLICK_TYPE.CANCEL
                        )}">`
                    ),
                    close_button: markup("</button>"),
                    icon: markup(
                        `<i class='fa fa-times-circle pe-1' data-type="${escape(
                            EDIT_CLICK_TYPE.CANCEL
                        )}"></i>`
                    ),
                    open_em: markup(`<em data-type="${escape(EDIT_CLICK_TYPE.CANCEL)}">`),
                    close_em: markup("</em>"),
                }
            );
        } else {
            const tags = {
                open_samp: markup("<samp>"),
                close_samp: markup("</samp>"),
                open_em: markup("<em>"),
                close_em: markup("</em>"),
                open_cancel: markup(
                    `<a role="button" href="#" data-type="${escape(EDIT_CLICK_TYPE.CANCEL)}">`
                ),
                close_cancel: markup("</a>"),
                open_save: markup(
                    `<a role="button" href="#" data-type="${escape(EDIT_CLICK_TYPE.SAVE)}">`
                ),
                close_save: markup("</a>"),
            };
            return this.env.inChatter
                ? _t(
                      "%(open_samp)sEscape%(close_samp)s %(open_em)sto %(open_cancel)scancel%(close_cancel)s%(close_em)s, %(open_samp)sCTRL-Enter%(close_samp)s %(open_em)sto %(open_save)ssave%(close_save)s%(close_em)s",
                      tags
                  )
                : _t(
                      "%(open_samp)sEscape%(close_samp)s %(open_em)sto %(open_cancel)scancel%(close_cancel)s%(close_em)s, %(open_samp)sEnter%(close_samp)s %(open_em)sto %(open_save)ssave%(close_save)s%(close_em)s",
                      tags
                  );
        }
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
        return !this.compact && this.props.sidebar;
    }

    get thread() {
        return this.props.messageToReplyTo?.message?.thread ?? this.props.composer.thread ?? null;
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
            (!this.props.composer.text && attachments.length === 0) ||
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
            onSelect: (ev, option) => {
                this.suggestion.insert(option);
                markEventHandled(ev, "composer.selectSuggestion");
            },
            isLoading: !!this.suggestion.search.term && this.suggestion.state.isFetching,
            options: [],
        };
        if (!this.hasSuggestions) {
            return props;
        }
        const suggestions = this.suggestion.state.items.suggestions;
        switch (this.suggestion.state.items.type) {
            case "Partner":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionPartner",
                    options: suggestions.map((suggestion) => {
                        if (suggestion.isSpecial) {
                            return {
                                ...suggestion,
                                group: 1,
                                optionTemplate: "mail.Composer.suggestionSpecial",
                                classList: "o-mail-Composer-suggestion",
                            };
                        } else {
                            return {
                                label: suggestion.name,
                                partner: suggestion,
                                classList: "o-mail-Composer-suggestion",
                            };
                        }
                    }),
                };
            case "Thread":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionThread",
                    options: suggestions.map((suggestion) => ({
                        label: suggestion.parent_channel_id
                            ? `${suggestion.parent_channel_id.displayName} > ${suggestion.displayName}`
                            : suggestion.displayName,
                        thread: suggestion,
                        classList: "o-mail-Composer-suggestion",
                    })),
                };
            case "ChannelCommand":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionChannelCommand",
                    options: suggestions.map((suggestion) => ({
                        label: suggestion.name,
                        help: suggestion.help,
                        classList: "o-mail-Composer-suggestion",
                    })),
                };
            case "mail.canned.response":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionCannedResponse",
                    options: suggestions.map((suggestion) => ({
                        cannedResponse: suggestion,
                        source: suggestion.source,
                        label: suggestion.substitution,
                        classList: "o-mail-Composer-suggestion",
                    })),
                };
            case "emoji":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionEmoji",
                    options: suggestions.map((suggestion) => ({
                        emoji: suggestion,
                        label: suggestion.codepoints,
                    })),
                };
            default:
                return props;
        }
    }

    onDropFile(ev) {
        if (isDragSourceExternalFile(ev.dataTransfer)) {
            for (const file of ev.dataTransfer.files) {
                this.attachmentUploader.uploadFile(file);
            }
        }
    }

    onCloseFullComposerCallback(isDiscard) {
        if (this.props.onCloseFullComposerCallback) {
            this.props.onCloseFullComposerCallback(isDiscard);
        } else {
            this.thread?.fetchNewMessages();
        }
    }

    onInput(ev) {
        if (!this.props.composer.isDirty) {
            this.props.composer.isDirty = true;
        }
    }

    /**
     * This doesn't work on firefox https://bugzilla.mozilla.org/show_bug.cgi?id=1699743
     */
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
        for (const file of ev.clipboardData.files) {
            this.attachmentUploader.uploadFile(file);
        }
    }

    onKeydown(ev) {
        const composer = toRaw(this.props.composer);
        switch (ev.key) {
            case "ArrowUp":
                if (this.props.messageEdition && composer.text === "") {
                    const messageToEdit = composer.thread.lastEditableMessageOfSelf;
                    if (messageToEdit) {
                        this.props.messageEdition.enterEditMode(messageToEdit);
                    }
                }
                break;
            case "Enter": {
                if (isEventHandled(ev, "NavigableList.select") || !this.state.active) {
                    ev.preventDefault();
                    return;
                }
                if (this.isMobileOS) {
                    return;
                }
                const shouldPost = this.env.inChatter ? ev.ctrlKey : !ev.shiftKey;
                if (!shouldPost) {
                    return;
                }
                ev.preventDefault(); // to prevent useless return
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
                    this.props.onDiscardCallback();
                    markEventHandled(ev, "Composer.discard");
                }
                break;
        }
    }

    async onClickFullComposer(ev) {
        const allRecipients = [...this.thread.suggestedRecipients];
        if (this.props.type !== "note") {
            allRecipients.push(...this.thread.additionalRecipients);
            // auto-create partners:
            const newPartners = allRecipients.filter((recipient) => !recipient.persona);
            if (newPartners.length !== 0) {
                const recipientEmails = [];
                newPartners.forEach((recipient) => {
                    recipientEmails.push(recipient.email);
                });
                const partners = await rpc("/mail/partner/from_email", {
                    thread_model: this.thread.model,
                    thread_id: this.thread.id,
                    emails: recipientEmails,
                });
                for (const index in partners) {
                    const partnerData = partners[index];
                    const persona = this.store.Persona.insert({ ...partnerData, type: "partner" });
                    const email = recipientEmails[index];
                    const recipient = allRecipients.find((recipient) => recipient.email === email);
                    Object.assign(recipient, { persona });
                }
            }
        }
        const attachmentIds = this.props.composer.attachments.map((attachment) => attachment.id);
        const body = this.props.composer.text;
        const validMentions = this.store.getMentionsFromText(body, {
            mentionedChannels: this.props.composer.mentionedChannels,
            mentionedPartners: this.props.composer.mentionedPartners,
        });
        let default_body = await prettifyMessageContent(body, validMentions);
        if (!default_body) {
            const composer = toRaw(this.props.composer);
            // Reset signature when recovering an empty body.
            composer.emailAddSignature = true;
        }
        let signature = this.thread.effectiveSelf.signature;
        if (signature) {
            const doc = createDocumentFragmentFromContent(signature);
            const divElement = document.createElement("div");
            divElement.setAttribute("data-o-mail-quote", "1");
            const br = document.createElement("br");
            const textNode = document.createTextNode("-- ");
            divElement.append(textNode, br, ...doc.body.childNodes);
            signature = markup(divElement.outerHTML);
        }
        default_body = this.formatDefaultBodyForFullComposer(
            default_body,
            this.props.composer.emailAddSignature ? signature : ""
        );
        const context = {
            default_attachment_ids: attachmentIds,
            default_body,
            default_email_add_signature: false,
            default_model: this.thread.model,
            default_partner_ids:
                this.props.type === "note"
                    ? []
                    : allRecipients.map((recipient) => recipient.persona.id),
            default_res_ids: [this.thread.id],
            default_subtype_xmlid: this.props.type === "note" ? "mail.mt_note" : "mail.mt_comment",
            clicked_on_full_composer: true,
            // Changed in 18.2+: finally get rid of autofollow, following should be done manually
        };
        const action = {
            name: this.props.type === "note" ? _t("Log note") : _t("Compose Email"),
            type: "ir.actions.act_window",
            res_model: "mail.compose.message",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: context,
        };
        const options = {
            onClose: (args) => {
                // args === { dismiss: true } : click on 'X' or press escape
                // args === { special: true } : click on 'discard'
                const accidentalDiscard = args?.dismiss;
                const isDiscard = accidentalDiscard || args?.special;
                // otherwise message is posted (args === [undefined])
                if (!isDiscard && this.props.composer.thread.model === "mail.box") {
                    this.notifySendFromMailbox();
                }
                if (accidentalDiscard) {
                    this.fullComposerBus.trigger("ACCIDENTAL_DISCARD", {
                        onAccidentalDiscard: (isEmpty) => {
                            if (!isEmpty) {
                                this.saveContent();
                                this.restoreContent();
                            }
                        },
                    });
                } else {
                    this.clear();
                }
                this.props.messageToReplyTo?.cancel();
                this.onCloseFullComposerCallback(isDiscard);
                this.state.isFullComposerOpen = false;
                // Use another event bus so that no message is sent to the
                // closed composer.
                this.fullComposerBus = new EventBus();
            },
            props: {
                fullComposerBus: this.fullComposerBus,
            },
        };
        await this.env.services.action.doAction(action, options);
        this.state.isFullComposerOpen = true;
    }

    /**
     * @param {string|ReturnType<markup>} defaultBody
     * @param {string|ReturnType<markup>} [signature=""]
     * @returns {ReturnType<markup>}
     */
    formatDefaultBodyForFullComposer(defaultBody, signature = "") {
        if (signature) {
            defaultBody = htmlJoin(defaultBody, markup("<br>"), signature);
        }
        return htmlJoin(markup("<div>"), defaultBody, markup("</div>")); // as to not wrap in <p> by html_sanitize
    }

    clear() {
        this.props.composer.clear();
        browser.localStorage.removeItem(this.props.composer.localId);
    }

    notifySendFromMailbox() {
        this.env.services.notification.add(_t('Message posted on "%s"', this.thread.displayName), {
            type: "info",
        });
    }

    isEventTrusted(ev) {
        // Allow patching during tests
        return ev.isTrusted;
    }

    async processMessage(cb) {
        const attachments = this.props.composer.attachments;
        if (attachments.some(({ uploading }) => uploading)) {
            this.env.services.notification.add(_t("Please wait while the file is uploading."), {
                type: "warning",
            });
        } else if (
            this.props.composer.text.trim() ||
            attachments.length > 0 ||
            (this.message && this.message.attachment_ids.length > 0)
        ) {
            if (!this.state.active) {
                return;
            }
            this.state.active = false;
            await cb(this.props.composer.text);
            if (this.props.onPostCallback) {
                this.props.onPostCallback();
            }
            this.clear();
            this.state.active = true;
            this.ref.el?.focus();
        }
    }

    async sendMessage() {
        const composer = toRaw(this.props.composer);
        this.composerActions.activePicker?.close?.();
        if (composer.message) {
            this.editMessage();
            return;
        }
        if (this.props.type !== "note") {
            const allRecipients = [
                ...composer.thread.suggestedRecipients,
                ...composer.thread.additionalRecipients,
            ];
            if (allRecipients.some((recipient) => !recipient.email || !isEmail(recipient.email))) {
                return;
            }
        }
        await this.processMessage(async (value) => {
            await this._sendMessage(value, this.postData, this.extraData);
        });
    }

    get postData() {
        const composer = toRaw(this.props.composer);
        return {
            attachments: composer.attachments || [],
            emailAddSignature: composer.emailAddSignature,
            isNote: this.props.type === "note",
            mentionedChannels: composer.mentionedChannels || [],
            mentionedPartners: composer.mentionedPartners || [],
            cannedResponseIds: composer.cannedResponses.map((c) => c.id),
            parentId: this.props.messageToReplyTo?.message?.id,
        };
    }

    /**
     * @typedef postData
     * @property {import("models").Attachment[]} attachments
     * @property {boolean} isNote
     * @property {number} parentId
     * @property {integer[]} mentionedChannelIds
     * @property {integer[]} mentionedPartnerIds
     */

    /**
     * @param {string} value message body
     * @param {postData} postData Message meta data info
     * @param {extraData} extraData Message extra meta data info needed by other modules
     */
    async _sendMessage(value, postData, extraData) {
        const thread = toRaw(this.props.composer.thread);
        const postThread = toRaw(this.thread);
        const post = postThread.post.bind(postThread, value, postData, extraData);
        if (postThread.model === "discuss.channel") {
            // feature of (optimistic) temp message
            post();
        } else {
            await post();
        }
        if (thread.model === "mail.box") {
            this.notifySendFromMailbox();
        }
        this.suggestion?.clearRawMentions();
        this.suggestion?.clearCannedResponses();
        this.props.messageToReplyTo?.cancel();
        this.props.composer.emailAddSignature = true;
        this.props.composer.thread.additionalRecipients = [];
    }

    async editMessage() {
        const composer = toRaw(this.props.composer);
        if (composer.text || composer.message.attachment_ids.length > 0) {
            await this.processMessage(async (value) =>
                composer.message.edit(value, composer.attachments, {
                    mentionedChannels: composer.mentionedChannels,
                    mentionedPartners: composer.mentionedPartners,
                })
            );
        } else {
            this.env.services.dialog.add(MessageConfirmDialog, {
                message: composer.message,
                onConfirm: () => {
                    this.message.remove({
                        removeFromThread: this.shouldHideFromMessageListOnDelete,
                    });
                    this.props.onDiscardCallback?.();
                },
                prompt: _t("Are you sure you want to delete this message?"),
            });
        }
        this.suggestion?.clearRawMentions();
    }

    onClickInsertCannedResponse(ev) {
        markEventHandled(ev, "composer.clickInsertCannedResponse");
        const composer = toRaw(this.props.composer);
        const text = composer.text;
        const firstPart = text.slice(0, composer.selection.start);
        const secondPart = text.slice(composer.selection.end, text.length);
        const toInsertPart = firstPart.length === 0 || firstPart.at(-1) === " " ? "::" : " ::";
        composer.text = firstPart + toInsertPart + secondPart;
        this.selection.moveCursor((firstPart + toInsertPart).length);
        if (!this.ui.isSmall || !this.env.inChatter) {
            composer.autofocus++;
        }
    }

    addEmoji(str) {
        const composer = toRaw(this.props.composer);
        const text = composer.text;
        const firstPart = text.slice(0, composer.selection.start);
        const secondPart = text.slice(composer.selection.end, text.length);
        composer.text = firstPart + str + secondPart;
        this.selection.moveCursor((firstPart + str).length);
        if (this.ui.isSmall && !this.env.inChatter) {
            return false;
        } else {
            composer.autofocus++;
        }
    }

    onFocusin() {
        const composer = toRaw(this.props.composer);
        composer.isFocused = true;
        if (
            composer.thread?.scrollTop === "bottom" &&
            !composer.thread.scrollUnread &&
            !composer.thread.markedAsUnread
        ) {
            composer.thread?.markAsRead();
        }
    }

    onFocusout(ev) {
        if (
            [EDIT_CLICK_TYPE.CANCEL, EDIT_CLICK_TYPE.SAVE].includes(ev.relatedTarget?.dataset?.type)
        ) {
            // Edit or Save most likely clicked: early return as to not re-render (which prevents click)
            return;
        }
        this.props.composer.isFocused = false;
    }

    saveContent() {
        const composer = toRaw(this.props.composer);
        const saveContentToLocalStorage = (text, emailAddSignature) => {
            const config = {
                emailAddSignature,
                text,
            };
            browser.localStorage.setItem(composer.localId, JSON.stringify(config));
        };
        if (this.state.isFullComposerOpen) {
            this.fullComposerBus.trigger("SAVE_CONTENT", {
                onSaveContent: saveContentToLocalStorage,
            });
        } else {
            saveContentToLocalStorage(composer.text, true);
        }
    }

    restoreContent() {
        const composer = toRaw(this.props.composer);
        let config;
        try {
            config = JSON.parse(browser.localStorage.getItem(composer.localId));
        } catch {
            browser.localStorage.removeItem(composer.localId);
        }
        if (config && config.text) {
            composer.emailAddSignature = config.emailAddSignature;
            composer.text = config.text;
        }
    }

    get shouldHideFromMessageListOnDelete() {
        return false;
    }
}
