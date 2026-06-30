import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { ScheduledMessage } from "@mail/chatter/web/scheduled_message";
import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { usePopoutAttachment } from "@mail/core/common/attachment_view";
import { MailAttachmentDropzone } from "@mail/core/common/mail_attachment_dropzone";
import { MessageCardList } from "@mail/core/common/message_card_list";
import { useMessageSearch } from "@mail/core/common/message_search_hook";
import { SearchMessageInput } from "@mail/core/common/search_message_input";
import { SearchMessageResult } from "@mail/core/common/search_message_result";
import { Activity } from "@mail/core/web/activity";
import { FollowerList } from "@mail/core/web/follower_list";
import { useHover, useOnChange } from "@mail/utils/common/hooks";
import { assignGetter, isDragSourceExternalFile } from "@mail/utils/common/misc";

import { props, status, t } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { Record } from "@web/model/relational_model/record";
import { FileUploader } from "@web/views/fields/file_handler";

export const DELAY_FOR_SPINNER = 1000;

Object.assign(Chatter.components, {
    Activity,
    AttachmentList,
    Dropdown,
    FileUploader,
    FollowerList,
    MessageCardList,
    ScheduledMessage,
    SearchMessageInput,
    SearchMessageResult,
});

/**
 * @type {import("@mail/chatter/web_portal_project/chatter").Chatter }
 * @typedef {Object} Props
 * @property {function} [close]
 */
const chatterPatch = {
    setup() {
        super.setup(...arguments);
        this.webChatterProps = props({
            close: t.function([]).optional(),
            has_activities: t.boolean().optional(true),
            hasAttachmentPreview: t.boolean().optional(false),
            hasParentReloadOnActivityChanged: t.boolean().optional(false),
            hasParentReloadOnAttachmentsChanged: t.boolean().optional(false),
            hasParentReloadOnFollowersUpdate: t.boolean().optional(false),
            hasParentReloadOnMessagePosted: t.boolean().optional(false),
            isAttachmentBoxVisibleInitially: t.boolean().optional(false),
            isChatterAside: t.boolean().optional(false),
            isInFormSheetBg: t.boolean().optional(true),
            record: t.instanceOf(Record).optional(),
            saveRecord: t.function([]).optional(),
        });
        this.orm = useService("orm");
        this.keepLastSuggestedRecipientsUpdate = new KeepLast();
        useOnChange(
            () => {
                const record = this.webChatterProps.record;
                // Track the record identity + all of its field changes.
                if (record?.data) {
                    Object.keys(record.data).forEach((field) => record.data[field]);
                }
                return [record];
            },
            (record) => this.updateRecipients(record)
        );
        this.attachmentPopout = usePopoutAttachment();
        Object.assign(this.state, {
            composerType: false,
            isAttachmentBoxOpened: this.webChatterProps.isAttachmentBoxVisibleInitially,
            isSearchOpen: false,
            showActivities: true,
            showAttachmentLoading: false,
            showPinnedMessages: false,
            showScheduledMessages: true,
        });
        this.messageSearch = useMessageSearch();
        this.attachmentUploader = useAttachmentUploader(
            this.store["mail.thread"].insert({
                model: this.props.threadModel,
                id: this.props.threadId,
            })
        );
        this.unfollowHover = useHover("unfollow");
        this.followerListDropdown = useDropdownState();
        /** @type {number|null} */
        this.loadingAttachmentTimeout = null;
        this.subjectInputRef = useRef("subjectInput");
        /** @type {Map<string, Function>} */
        this.uploadHandlers = new Map();
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
                            const saved = await this.webChatterProps.saveRecord?.();
                            if (!saved) {
                                return;
                            }
                        }
                        Promise.all(
                            files.map((file) => this.attachmentUploader.uploadFile(file))
                        ).then(() => {
                            if (this.webChatterProps.hasParentReloadOnAttachmentsChanged) {
                                this.reloadParentView();
                            }
                        });
                        this.state.isAttachmentBoxOpened = true;
                    }
                },
            },
            () =>
                (!this.store.meetingViewOpened || this.env.inMeetingView) &&
                (this.state.thread?.isTransient || this.state.thread?.canPostMessage)
        );
        useLayoutEffect(
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
                        (this.webChatterProps.isAttachmentBoxVisibleInitially &&
                            this.attachments.length > 0);
                }
                return () => browser.clearTimeout(this.loadingAttachmentTimeout);
            },
            () => [this.state.thread, this.state.thread?.isLoadingAttachments]
        );
        useLayoutEffect(
            (status, attachmentsLength) => {
                if (!["new", "loading"].includes(status) && attachmentsLength === 0) {
                    this.state.isAttachmentBoxOpened = false;
                }
            },
            () => [this.state.thread?.status, this.attachments.length]
        );
    },

    async updateRecipients(record, mode = this.state.composerType) {
        if (!record) {
            return;
        }
        const partnerIds = []; // Ensure that we don't have duplicates
        let email;
        (this.state.thread?.partner_fields ?? []).forEach((field) => {
            const value = record._changes[field];
            if (record.data[field] !== undefined && value) {
                partnerIds.push(value.id);
            }
        });
        const field = this.state.thread?.primary_email_field;
        if (field) {
            const value = record._changes[field];
            if (record.data[field] !== undefined && value) {
                email = value;
            }
        }
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
            recipient_type: result.recipient_type,
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
            "suggestedSubject",
        ];
    },

    get attachments() {
        return this.state.thread?.attachments ?? [];
    },

    get childSubEnv() {
        const res = super.childSubEnv;
        assignGetter(res.inChatter, { aside: () => this.webChatterProps.isChatterAside });
        Object.assign(res.inChatter, { toggleComposer: this.toggleComposer.bind(this) });
        return res;
    },

    get followerButtonLabel() {
        return _t("Show Followers");
    },

    get followingText() {
        return _t("Following");
    },
    get hasPinnedMessages() {
        return (
            this.state.thread?.has_pinned_messages || this.state.thread?.pinnedMessages?.length > 0
        );
    },
    /**
     * @returns {boolean}
     */
    get isDisabled() {
        return !this.state.thread.id || !this.state.thread?.hasReadAccess;
    },

    get requestList() {
        return [
            ...super.requestList,
            "activities",
            "attachments",
            "contact_fields",
            "defaultSubject",
            "followers",
            "has_pinned_messages",
            "scheduledMessages",
            "showSubjectInSmallComposer",
            "suggestedRecipients",
            "suggestedSubject",
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
        if (!thread?.id || !this.state.thread?.eq(thread)) {
            return;
        }
        this.updateRecipients(this.webChatterProps.record);
    },

    onActivityChanged(thread) {
        this.load(thread, this.initialRequestList);
        if (this.webChatterProps.hasParentReloadOnActivityChanged) {
            this.reloadParentView();
        }
    },

    onAddFollowers() {
        this.load(this.state.thread, ["followers", "suggestedRecipients"]);
        if (this.webChatterProps.hasParentReloadOnFollowersUpdate) {
            this.reloadParentView();
        }
    },

    onClickAddAttachments() {
        if (this.attachments.length === 0) {
            return;
        }
        this.state.isAttachmentBoxOpened = !this.state.isAttachmentBoxOpened;
        if (this.state.isAttachmentBoxOpened) {
            this.rootRef().scrollTop = 0;
            this.state.thread.scrollTop = "bottom";
        }
    },

    async onClickAttachFile(ev) {
        if (this.state.thread.id) {
            return;
        }
        const saved = await this.webChatterProps.saveRecord?.();
        if (!saved) {
            return false;
        }
    },
    onClickPinnedMessages() {
        this.state.showPinnedMessages = !this.state.showPinnedMessages;
        if (this.state.showPinnedMessages) {
            this.state.thread?.fetchPinnedMessages();
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

    /** @param {import("models").Thread} thread */
    onFollowerChanged(thread) {
        document.body.click(); // hack to close dropdown
        if (thread?.eq(this.state.thread)) {
            this.reloadParentView();
        }
    },

    onPostCallback() {
        if (this.webChatterProps.hasParentReloadOnMessagePosted) {
            this.reloadParentView();
        }
        this.toggleComposer();
        super.onPostCallback();
    },

    /** @param {import("models").Thread} thread */
    onScheduledMessageChanged(thread) {
        // reload messages as well as a scheduled message could have been sent
        this.load(thread, ["scheduledMessages", "messages"]);
        // sending a message could trigger another action (eg. move so to quotation sent)
        this.reloadParentView();
    },

    onSuggestedRecipientAdded(thread) {
        this.load(thread, ["suggestedRecipients"]);
    },

    /** @param {import("models").Thread} thread */
    onUploaded({ thread } = {}) {
        const threadLocalId = thread.localId;
        if (!this.uploadHandlers.has(threadLocalId)) {
            const self = this;
            this.uploadHandlers.set(threadLocalId, async function handleUpload(data) {
                try {
                    await self.attachmentUploader.uploadData(data, { thread });
                    if (!thread.eq(self.state.thread)) {
                        return;
                    }
                    if (self.webChatterProps.hasParentReloadOnAttachmentsChanged) {
                        self.reloadParentView();
                    }
                    self.state.isAttachmentBoxOpened = true;
                    if (self.rootRef()) {
                        self.rootRef().scrollTop = 0;
                    }
                    self.state.thread.scrollTop = "bottom";
                } finally {
                    self.uploadHandlers.delete(threadLocalId);
                }
            });
        }
        return this.uploadHandlers.get(threadLocalId);
    },

    async reloadParentView() {
        await this.webChatterProps.saveRecord?.();
        if (this.webChatterProps.record) {
            await this.webChatterProps.record.load();
        }
    },

    async scheduleActivity() {
        this.closeSearch();
        const schedule = async (thread) => {
            await this.store.scheduleActivity(thread.model, [thread.id]);
            this.load(thread, ["activities", "messages"]);
            if (this.webChatterProps.hasParentReloadOnActivityChanged) {
                await this.reloadParentView();
            }
        };
        if (this.state.thread.id) {
            schedule(this.state.thread);
        } else {
            this.onThreadCreated = schedule;
            this.webChatterProps.saveRecord?.();
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
                    await this.updateRecipients(this.webChatterProps.record, mode);
                }
                this.state.composerType = mode;
            }
        };
        if (this.state.thread.id) {
            toggle();
        } else {
            this.onThreadCreated = toggle;
            this.webChatterProps.saveRecord?.();
        }
    },

    toggleScheduledMessages() {
        this.state.showScheduledMessages = !this.state.showScheduledMessages;
    },

    async unlinkAttachment(attachment) {
        await this.attachmentUploader.unlink(attachment);
        if (this.webChatterProps.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
    },

    popoutAttachment() {
        this.attachmentPopout.popout();
    },
};
patch(Chatter.prototype, chatterPatch);
