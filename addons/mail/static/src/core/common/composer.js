import { AttachmentList } from "@mail/core/common/attachment_list";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { useDropzone } from "@web/core/dropzone/dropzone_hook";
import { Picker, usePicker } from "@mail/core/common/picker";
import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";
import { NavigableList } from "@mail/core/common/navigable_list";
import { useSuggestion } from "@mail/core/common/suggestion_hook";
import { prettifyMessageContent } from "@mail/utils/common/format";
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
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
    useExternalListener,
    toRaw,
} from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { escape, sprintf } from "@web/core/utils/strings";
import { isMobileOS } from "@web/core/browser/feature_detection";

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
        Picker,
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
        this.SEND_KEYBIND_TO_SEND = markup(
            _t("<samp>%(send_keybind)s</samp><i> to send</i>", { send_keybind: this.sendKeybind })
        );
        this.store = useState(useService("mail.store"));
        this.attachmentUploader = useAttachmentUploader(
            this.thread ?? this.props.composer.message.thread,
            { composer: this.props.composer }
        );
        this.ui = useState(useService("ui"));
        this.mainActionsRef = useRef("main-actions");
        this.ref = useRef("textarea");
        this.fakeTextarea = useRef("fakeTextarea");
        this.emojiButton = useRef("emoji-button");
        this.inputContainerRef = useRef("input-container");
        this.state = useState({
            active: true,
        });
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
                    isEventHandled(ev, "composer.selectSuggestion")
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
        if (this.props.dropzoneRef) {
            useDropzone(
                this.props.dropzoneRef,
                this.onDropFile,
                "o-mail-Composer-dropzone",
                () => this.allowUpload
            );
        }
        if (this.props.messageEdition) {
            this.props.messageEdition.composerOfThread = this;
        }
        useChildSubEnv({
            inComposer: true,
        });
        this.picker = usePicker(this.pickerSettings);
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
                    this.ref.el.style.height = this.fakeTextarea.el.scrollHeight + "px";
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
    }

    get pickerSettings() {
        return {
            anchor: this.props.mode === "extended" ? undefined : this.mainActionsRef,
            buttons: [this.emojiButton],
            close: () => {
                if (!this.ui.isSmall) {
                    this.props.composer.autofocus++;
                }
            },
            pickers: { emoji: (emoji) => this.addEmoji(emoji) },
            position:
                this.props.mode === "extended"
                    ? "bottom-start"
                    : this.props.composer.message
                    ? "bottom-start"
                    : "top-end",
            fixed: !this.props.composer.message,
        };
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
            return markup(
                sprintf(
                    escape(
                        _t(
                            "%(open_button)s%(icon)s%(open_em)sDiscard editing%(close_em)s%(close_button)s"
                        )
                    ),
                    {
                        open_button: `<button class='btn px-1 py-0' data-type="${escape(
                            EDIT_CLICK_TYPE.CANCEL
                        )}">`,
                        close_button: "</button>",
                        icon: `<i class='fa fa-times-circle pe-1' data-type="${escape(
                            EDIT_CLICK_TYPE.CANCEL
                        )}"></i>`,
                        open_em: `<em data-type="${escape(EDIT_CLICK_TYPE.CANCEL)}">`,
                        close_em: "</em>",
                    }
                )
            );
        } else {
            const translation1 = _t(
                "%(open_samp)sEscape%(close_samp)s %(open_em)sto %(open_cancel)scancel%(close_cancel)s%(close_em)s, %(open_samp)sCTRL-Enter%(close_samp)s %(open_em)sto %(open_save)ssave%(close_save)s%(close_em)s"
            );
            const translation2 = _t(
                "%(open_samp)sEscape%(close_samp)s %(open_em)sto %(open_cancel)scancel%(close_cancel)s%(close_em)s, %(open_samp)sEnter%(close_samp)s %(open_em)sto %(open_save)ssave%(close_save)s%(close_em)s"
            );
            return markup(
                sprintf(escape(this.props.mode === "extended" ? translation1 : translation2), {
                    open_samp: "<samp>",
                    close_samp: "</samp>",
                    open_em: "<em>",
                    close_em: "</em>",
                    open_cancel: `<a role="button" href="#" data-type="${escape(
                        EDIT_CLICK_TYPE.CANCEL
                    )}">`,
                    close_cancel: "</a>",
                    open_save: `<a role="button" href="#" data-type="${escape(
                        EDIT_CLICK_TYPE.SAVE
                    )}">`,
                    close_save: "</a>",
                })
            );
        }
    }

    get SEND_TEXT() {
        if (this.props.composer.message) {
            return _t("Save editing");
        }
        return this.props.type === "note" ? _t("Log") : _t("Send");
    }

    get sendKeybind() {
        return this.props.mode === "extended" ? _t("CTRL-Enter") : _t("Enter");
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

    get hasSendButtonNonEditing() {
        return !this.extended;
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
                    options: suggestions.map((suggestion) => {
                        return {
                            label: suggestion.parent_channel_id
                                ? `${suggestion.parent_channel_id.displayName} > ${suggestion.displayName}`
                                : suggestion.displayName,
                            thread: suggestion,
                            classList: "o-mail-Composer-suggestion",
                        };
                    }),
                };
            case "ChannelCommand":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionChannelCommand",
                    options: suggestions.map((suggestion) => {
                        return {
                            label: suggestion.name,
                            help: suggestion.help,
                            classList: "o-mail-Composer-suggestion",
                        };
                    }),
                };
            case "mail.canned.response":
                return {
                    ...props,
                    autoSelectFirst: false,
                    hint: _t("Tab to select"),
                    optionTemplate: "mail.Composer.suggestionCannedResponse",
                    options: suggestions.map((suggestion) => {
                        return {
                            cannedResponse: suggestion,
                            source: suggestion.source,
                            label: suggestion.substitution,
                            classList: "o-mail-Composer-suggestion",
                        };
                    }),
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

    onCloseFullComposerCallback() {
        if (this.props.onCloseFullComposerCallback) {
            this.props.onCloseFullComposerCallback();
        } else {
            this.thread?.fetchNewMessages();
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
                        this.props.messageEdition.editingMessage = messageToEdit;
                    }
                }
                break;
            case "Enter": {
                if (isEventHandled(ev, "NavigableList.select") || !this.state.active) {
                    ev.preventDefault();
                    return;
                }
                const shouldPost = this.props.mode === "extended" ? ev.ctrlKey : !ev.shiftKey;
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

    onClickAddAttachment(ev) {
        const composer = toRaw(this.props.composer);
        markEventHandled(ev, "composer.clickOnAddAttachment");
        composer.autofocus++;
    }

    async onClickFullComposer(ev) {
        if (this.props.type !== "note") {
            // auto-create partners of checked suggested partners
            const newPartners = this.thread.suggestedRecipients.filter(
                (recipient) => recipient.checked && !recipient.persona
            );
            if (newPartners.length !== 0) {
                const recipientEmails = [];
                const recipientAdditionalValues = {};
                newPartners.forEach((recipient) => {
                    recipientEmails.push(recipient.email);
                    recipientAdditionalValues[recipient.email] = recipient.create_values || {};
                });
                const partners = await rpc("/mail/partner/from_email", {
                    emails: recipientEmails,
                    additional_values: recipientAdditionalValues,
                });
                for (const index in partners) {
                    const partnerData = partners[index];
                    const persona = this.store.Persona.insert({ ...partnerData, type: "partner" });
                    const email = recipientEmails[index];
                    const recipient = this.thread.suggestedRecipients.find(
                        (recipient) => recipient.email === email
                    );
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
        const context = {
            default_attachment_ids: attachmentIds,
            default_body: await prettifyMessageContent(body, validMentions),
            default_model: this.thread.model,
            default_partner_ids:
                this.props.type === "note"
                    ? []
                    : this.thread.suggestedRecipients
                          .filter((recipient) => recipient.checked)
                          .map((recipient) => recipient.persona.id),
            default_res_ids: [this.thread.id],
            default_subtype_xmlid: this.props.type === "note" ? "mail.mt_note" : "mail.mt_comment",
            mail_post_autofollow: this.thread.hasWriteAccess,
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
            onClose: (...args) => {
                // args === [] : click on 'X'
                // args === { special: true } : click on 'discard'
                const isDiscard = args.length === 0 || args[0]?.special;
                // otherwise message is posted (args === [undefined])
                if (!isDiscard && this.props.composer.thread.model === "mail.box") {
                    this.notifySendFromMailbox();
                }
                if (
                    args.length === 0 &&
                    document
                        .querySelector(".o_mail_composer_form_view .note-editable")
                        .innerText.replace(/^\s*$/gm, "")
                ) {
                    this.saveContent();
                    this.restoreContent();
                } else {
                    this.clear();
                }
                this.props.messageToReplyTo?.cancel();
                this.onCloseFullComposerCallback();
            },
        };
        await this.env.services.action.doAction(action, options);
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

    onClickAddEmoji(ev) {
        markEventHandled(ev, "Composer.onClickAddEmoji");
    }

    isEventTrusted(ev) {
        // Allow patching during tests
        return ev.isTrusted;
    }

    async processMessage(cb) {
        const el = this.ref.el;
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
            el.focus();
        }
    }

    async sendMessage() {
        const composer = toRaw(this.props.composer);
        if (composer.message) {
            this.editMessage();
            return;
        }
        await this.processMessage(async (value) => {
            await this._sendMessage(value, this.postData, this.extraData);
        });
    }

    get postData() {
        const composer = toRaw(this.props.composer);
        return {
            attachments: composer.attachments || [],
            isNote: this.props.type === "note",
            mentionedChannels: composer.mentionedChannels || [],
            mentionedPartners: composer.mentionedPartners || [],
            cannedResponseIds: composer.cannedResponses.map((c) => c.id),
            parentId: this.props.messageToReplyTo?.message?.id,
        };
    }

    /**
     * @typedef postData
     * @property {import('@mail/attachments/attachment_model').Attachment[]} attachments
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
                onConfirm: () => this.message.remove(),
                prompt: _t("Are you sure you want to delete this message?"),
            });
        }
        this.suggestion?.clearRawMentions();
    }

    addEmoji(str) {
        const composer = toRaw(this.props.composer);
        const text = composer.text;
        const firstPart = text.slice(0, composer.selection.start);
        const secondPart = text.slice(composer.selection.end, text.length);
        composer.text = firstPart + str + secondPart;
        this.selection.moveCursor((firstPart + str).length);
        if (!this.ui.isSmall) {
            composer.autofocus++;
        }
    }

    onFocusin() {
        const composer = toRaw(this.props.composer);
        composer.isFocused = true;
        composer.thread?.markAsRead();
    }

    saveContent() {
        const composer = toRaw(this.props.composer);
        const fullComposerContent =
            document
                .querySelector(".o_mail_composer_form_view .note-editable")
                ?.innerText.replace(/(\t|\n)+/g, "\n") ?? composer.text;
        browser.localStorage.setItem(composer.localId, fullComposerContent);
    }

    restoreContent() {
        const composer = toRaw(this.props.composer);
        const fullComposerContent = browser.localStorage.getItem(composer.localId);
        if (fullComposerContent) {
            composer.text = fullComposerContent;
        }
    }
}
