import { ScheduledMessage } from "@mail/chatter/web/scheduled_message";
import { Activity } from "@mail/core/web/activity";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { FollowerList } from "@mail/core/web/follower_list";
import { assignGetter, isDragSourceExternalFile } from "@mail/utils/common/misc";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { useHover, useMessageScrolling } from "@mail/utils/common/hooks";
import { MailAttachmentDropzone } from "@mail/core/common/mail_attachment_dropzone";
import { RecipientsInput } from "@mail/core/web/recipients_input";
import { SearchMessageInput } from "@mail/core/common/search_message_input";
import { SearchMessageResult } from "@mail/core/common/search_message_result";
import { KeepLast } from "@web/core/utils/concurrency";
import { status, useEffect } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { FileUploader } from "@web/views/fields/file_handler";
import { patch } from "@web/core/utils/patch";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";
import { useMessageSearch } from "@mail/core/common/message_search_hook";
import { usePopoutAttachment } from "@mail/core/common/attachment_view";
import { rpc } from "@web/core/network/rpc";
import { useRecordObserver } from "@web/model/relational_model/utils";

export const DELAY_FOR_SPINNER = 1000;

Object.assign(Chatter.components, {
    Activity,
    AttachmentList,
    Dropdown,
    FileUploader,
    FollowerList,
    RecipientsInput,
    ScheduledMessage,
    SearchMessageInput,
    SearchMessageResult,
});

Chatter.props.push(
    "close?",
    "compactHeight?",
    "has_activities?",
    "hasAttachmentPreview?",
    "hasParentReloadOnActivityChanged?",
    "hasParentReloadOnAttachmentsChanged?",
    "hasParentReloadOnFollowersUpdate?",
    "hasParentReloadOnMessagePosted?",
    "highlightMessageId?",
    "isAttachmentBoxVisibleInitially?",
    "isChatterAside?",
    "isInFormSheetBg?",
    "saveRecord?",
    "record?"
);

Object.assign(Chatter.defaultProps, {
    compactHeight: false,
    has_activities: true,
    hasAttachmentPreview: false,
    hasParentReloadOnActivityChanged: false,
    hasParentReloadOnAttachmentsChanged: false,
    hasParentReloadOnFollowersUpdate: false,
    hasParentReloadOnMessagePosted: false,
    isAttachmentBoxVisibleInitially: false,
    isChatterAside: false,
    isInFormSheetBg: true,
});

/**
 * @type {import("@mail/chatter/web_portal/chatter").Chatter }
 * @typedef {Object} Props
 * @property {function} [close]
 */
patch(Chatter.prototype, {
    setup() {
        this.messageHighlight = useMessageScrolling();
        super.setup(...arguments);
        this.orm = useService("orm");
        this.keepLastSuggestedRecipientsUpdate = new KeepLast();
        /** @deprecated equivalent to partner_fields and primary_email_field on thread */
        this.mailImpactingFields = { recordFields: [], emailFields: [] };
        useRecordObserver((record) => this.updateRecipients(record));
        this.attachmentPopout = usePopoutAttachment();
        Object.assign(this.state, {
            composerType: false,
            isAttachmentBoxOpened: this.props.isAttachmentBoxVisibleInitially,
            isSearchOpen: false,
            showActivities: true,
            showAttachmentLoading: false,
            showScheduledMessages: true,
        });
        this.messageSearch = useMessageSearch();
        this.attachmentUploader = useAttachmentUploader(
            this.store.Thread.insert({ model: this.props.threadModel, id: this.props.threadId })
        );
        this.unfollowHover = useHover("unfollow");
        this.followerListDropdown = useDropdownState();
        /** @type {number|null} */
        this.loadingAttachmentTimeout = null;
        useCustomDropzone(
            this.rootRef,
            MailAttachmentDropzone,
            {
                extraClass: "o-mail-Chatter-dropzone",
                /** @param {Event} ev */
                onDrop: async (ev) => {
                    if (this.state.composerType) {
                        return;
                    }
                    if (isDragSourceExternalFile(ev.dataTransfer)) {
                        const files = [...ev.dataTransfer.files];
                        if (!this.state.thread.id) {
                            const saved = await this.props.saveRecord?.();
                            if (!saved) {
                                return;
                            }
                        }
                        Promise.all(
                            files.map((file) => this.attachmentUploader.uploadFile(file))
                        ).then(() => {
                            if (this.props.hasParentReloadOnAttachmentsChanged) {
                                this.reloadParentView();
                            }
                        });
                        this.state.isAttachmentBoxOpened = true;
                    }
                },
            },
            () => !this.store.meetingViewOpened || this.env.inMeetingView
        );
        useEffect(
            () => {
                if (!this.state.thread) {
                    return;
                }
                browser.clearTimeout(this.loadingAttachmentTimeout);
                if (this.state.thread?.isLoadingAttachments) {
                    this.loadingAttachmentTimeout = browser.setTimeout(
                        () => (this.state.showAttachmentLoading = true),
                        DELAY_FOR_SPINNER
                    );
                } else {
                    this.state.showAttachmentLoading = false;
                    this.state.isAttachmentBoxOpened =
                        this.state.isAttachmentBoxOpened ||
                        (this.props.isAttachmentBoxVisibleInitially && this.attachments.length > 0);
                }
                return () => browser.clearTimeout(this.loadingAttachmentTimeout);
            },
            () => [this.state.thread, this.state.thread?.isLoadingAttachments]
        );
        useEffect(
            () => {
                if (
                    this.state.thread &&
                    !["new", "loading"].includes(this.state.thread.status) &&
                    this.attachments.length === 0
                ) {
                    this.state.isAttachmentBoxOpened = false;
                }
            },
            () => [this.state.thread?.status, this.attachments]
        );
        useEffect(
            () => {
                this.state.aside = this.props.isChatterAside;
            },
            () => [this.props.isChatterAside]
        );
    },

    async updateRecipients(record, mode = this.state.composerType) {
        if (!record) {
            return;
        }
        // Hack: Make the useRecordObserver subscribe to the record changes
        Object.keys(record.data).forEach((field) => record.data[field]);
        const partnerIds = []; // Ensure that we don't have duplicates
        let email;
        this.mailImpactingFields.recordFields.forEach((field) => {
            const value = record._changes[field];
            if (record.data[field] !== undefined && value) {
                partnerIds.push(value.id);
            }
        });
        this.mailImpactingFields.emailFields.forEach((field) => {
            const value = record._changes[field];
            if (record.data[field] !== undefined && value) {
                email = value;
                return;
            }
        });
        if ((!partnerIds.length && !email) || mode !== "message" || status(this) === "destroyed") {
            return;
        }
        const recipients = await this.keepLastSuggestedRecipientsUpdate.add(
            rpc("/mail/thread/recipients/get_suggested_recipients", {
                thread_model: this.props.threadModel,
                thread_id: this.props.threadId,
                partner_ids: partnerIds,
                main_email: email,
            })
        );
        if (status(this) === "destroyed" && !this.state.thread) {
            return;
        }
        this.state.thread.suggestedRecipients = recipients.map((result) => ({
            display_name: result.display_name,
            email: result.email,
            partner_id: result.partner_id,
            name: result.name || result.email,
        }));
        this.state.thread.additionalRecipients = this.state.thread.additionalRecipients.filter(
            (additionalRecipient) =>
                this.state.thread.suggestedRecipients.every(
                    (suggestedRecipient) =>
                        suggestedRecipient.partner_id !== additionalRecipient.partner_id
                )
        );
    },

    /**
     * @returns {import("models").Activity[]}
     */
    get activities() {
        return this.state.thread?.activities ?? [];
    },

    get afterPostRequestList() {
        return [
            ...super.afterPostRequestList,
            "followers",
            "scheduledMessages",
            "suggestedRecipients",
        ];
    },

    get attachments() {
        return this.state.thread?.attachments ?? [];
    },

    get childSubEnv() {
        const res = Object.assign(super.childSubEnv, { messageHighlight: this.messageHighlight });
        assignGetter(res.inChatter, { aside: () => this.props.isChatterAside });
        Object.assign(res.inChatter, { toggleComposer: this.toggleComposer.bind(this) });
        return res;
    },

    get followerButtonLabel() {
        return _t("Show Followers");
    },

    get followingText() {
        return _t("Following");
    },

    /**
     * @returns {boolean}
     */
    get isDisabled() {
        return !this.state.thread.id || !this.state.thread?.hasReadAccess;
    },

    get onCloseFullComposerRequestList() {
        return [...super.onCloseFullComposerRequestList, "scheduledMessages"];
    },

    get requestList() {
        return [
            ...super.requestList,
            "activities",
            "attachments",
            "contact_fields",
            "followers",
            "scheduledMessages",
            "suggestedRecipients",
        ];
    },

    get scheduledMessages() {
        return this.state.thread?.scheduledMessages ?? [];
    },

    get unfollowText() {
        return _t("Unfollow");
    },

    changeThread(threadModel, threadId) {
        super.changeThread(...arguments);
        this.attachmentUploader.thread = this.state.thread;
        if (threadId === false) {
            this.state.composerType = false;
        } else {
            this.onThreadCreated?.(this.state.thread);
            this.onThreadCreated = null;
            this.messageSearch.thread = this.state.thread;
            this.closeSearch();
        }
    },

    closeSearch() {
        this.messageSearch.clear();
        this.state.isSearchOpen = false;
    },

    /** @override */
    async load(thread, requestList) {
        await super.load(...arguments);
        if (!thread.id || !this.state.thread?.eq(thread)) {
            return;
        }
        this.mailImpactingFields = {
            emailFields: this.state.thread.primary_email_field
                ? [this.state.thread.primary_email_field]
                : [],
            recordFields: this.state.thread.partner_fields || [],
        };
        this.updateRecipients(this.props.record);
    },

    onActivityChanged(thread) {
        this.load(thread, [...this.requestList, "messages"]);
        if (this.props.hasParentReloadOnActivityChanged) {
            this.reloadParentView();
        }
    },

    onAddFollowers() {
        this.load(this.state.thread, ["followers", "suggestedRecipients"]);
        if (this.props.hasParentReloadOnFollowersUpdate) {
            this.reloadParentView();
        }
    },

    onClickAddAttachments() {
        if (this.attachments.length === 0) {
            return;
        }
        this.state.isAttachmentBoxOpened = !this.state.isAttachmentBoxOpened;
        if (this.state.isAttachmentBoxOpened) {
            this.rootRef.el.scrollTop = 0;
            this.state.thread.scrollTop = "bottom";
        }
    },

    async onClickAttachFile(ev) {
        if (this.state.thread.id) {
            return;
        }
        const saved = await this.props.saveRecord?.();
        if (!saved) {
            return false;
        }
    },

    onClickSearch() {
        this.state.composerType = false;
        this.state.isSearchOpen = !this.state.isSearchOpen;
    },

    onCloseFullComposerCallback(isDiscard) {
        this.toggleComposer();
        super.onCloseFullComposerCallback();
        if (!isDiscard) {
            this.reloadParentView();
        }
    },

    onFollowerChanged() {
        document.body.click(); // hack to close dropdown
        this.reloadParentView();
    },

    _onMounted() {
        super._onMounted();
        if (this.state.thread && this.props.highlightMessageId) {
            this.state.thread.highlightMessage = this.props.highlightMessageId;
        }
    },

    onPostCallback() {
        if (this.props.hasParentReloadOnMessagePosted) {
            this.reloadParentView();
        }
        this.toggleComposer();
        super.onPostCallback();
    },

    onScheduledMessageChanged(thread) {
        // reload messages as well as a scheduled message could have been sent
        this.load(thread, ["scheduledMessages", "messages"]);
        // sending a message could trigger another action (eg. move so to quotation sent)
        this.reloadParentView();
    },

    onSuggestedRecipientAdded(thread) {
        this.load(thread, ["suggestedRecipients"]);
    },

    async onUploaded(data) {
        await this.attachmentUploader.uploadData(data);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
        this.state.isAttachmentBoxOpened = true;
        if (this.rootRef.el) {
            this.rootRef.el.scrollTop = 0;
        }
        this.state.thread.scrollTop = "bottom";
    },

    async reloadParentView() {
        await this.props.saveRecord?.();
        if (this.props.record) {
            await this.props.record.load();
        }
    },

    async scheduleActivity() {
        this.closeSearch();
        const schedule = async (thread) => {
            await this.store.scheduleActivity(thread.model, [thread.id]);
            this.load(thread, ["activities", "messages"]);
            if (this.props.hasParentReloadOnActivityChanged) {
                await this.reloadParentView();
            }
        };
        if (this.state.thread.id) {
            schedule(this.state.thread);
        } else {
            this.onThreadCreated = schedule;
            this.props.saveRecord?.();
        }
    },

    toggleActivities() {
        this.state.showActivities = !this.state.showActivities;
    },

    toggleComposer(mode = false, { force = false } = {}) {
        this.closeSearch();
        const toggle = async () => {
            if (!force && this.state.composerType === mode) {
                this.state.composerType = false;
            } else {
                if (mode === "message") {
                    await this.updateRecipients(this.props.record, mode);
                }
                this.state.composerType = mode;
            }
        };
        if (this.state.thread.id) {
            toggle();
        } else {
            this.onThreadCreated = toggle;
            this.props.saveRecord?.();
        }
    },

    toggleScheduledMessages() {
        this.state.showScheduledMessages = !this.state.showScheduledMessages;
    },

    async unlinkAttachment(attachment) {
        await this.attachmentUploader.unlink(attachment);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
    },

    popoutAttachment() {
        this.attachmentPopout.popout();
    },
});
