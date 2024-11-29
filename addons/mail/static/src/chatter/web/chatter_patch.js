import { ScheduledMessage } from "@mail/chatter/web/scheduled_message";
import { Activity } from "@mail/core/web/activity";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { BaseRecipientsList } from "@mail/core/web/base_recipients_list";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { SuggestedRecipientsList } from "@mail/core/web/suggested_recipient_list";
import { FollowerList } from "@mail/core/web/follower_list";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { useDropzone } from "@web/core/dropzone/dropzone_hook";
import { useHover, useMessageHighlight } from "@mail/utils/common/hooks";
import { SearchMessageInput } from "@mail/core/common/search_message_input";
import { SearchMessageResult } from "@mail/core/common/search_message_result";

import { useEffect } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { FileUploader } from "@web/views/fields/file_handler";
import { patch } from "@web/core/utils/patch";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";
import { useMessageSearch } from "@mail/core/common/message_search_hook";
import { usePopoutAttachment } from "@mail/core/common/attachment_view";

export const DELAY_FOR_SPINNER = 1000;

Object.assign(Chatter.components, {
    Activity,
    AttachmentList,
    BaseRecipientsList,
    Dropdown,
    FileUploader,
    FollowerList,
    ScheduledMessage,
    SearchMessageInput,
    SearchMessageResult,
    SuggestedRecipientsList,
});

Chatter.props.push(
    "close?",
    "compactHeight?",
    "has_activities?",
    "hasAttachmentPreview?",
    "hasParentReloadOnAttachmentsChanged?",
    "hasParentReloadOnFollowersUpdate?",
    "hasParentReloadOnMessagePosted?",
    "highlightMessageId?",
    "isAttachmentBoxVisibleInitially?",
    "isChatterAside?",
    "isInFormSheetBg?",
    "saveRecord?",
    "webRecord?"
);

Object.assign(Chatter.defaultProps, {
    compactHeight: false,
    has_activities: true,
    hasAttachmentPreview: false,
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
        this.messageHighlight = useMessageHighlight();
        super.setup(...arguments);
        this.orm = useService("orm");
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
        useDropzone(
            this.rootRef,
            async (ev) => {
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
                    Promise.all(files.map((file) => this.attachmentUploader.uploadFile(file))).then(
                        () => {
                            if (this.props.hasParentReloadOnAttachmentsChanged) {
                                this.reloadParentView();
                            }
                        }
                    );
                    this.state.isAttachmentBoxOpened = true;
                }
            },
            "o-mail-Chatter-dropzone"
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
                        this.props.isAttachmentBoxVisibleInitially && this.attachments.length > 0;
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
        res.inChatter.aside = this.props.isChatterAside;
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

    async _follow(thread) {
        await this.orm.call(thread.model, "message_subscribe", [[thread.id]], {
            partner_ids: [this.store.self.id],
        });
        this.onFollowerChanged(thread);
    },

    onActivityChanged(thread) {
        this.load(thread, [...this.requestList, "messages"]);
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

    async onClickFollow() {
        if (this.state.thread.id) {
            this._follow(this.state.thread);
        } else {
            this.onThreadCreated = this._follow;
            await this.props.saveRecord?.();
        }
    },

    onClickSearch() {
        this.state.composerType = false;
        this.state.isSearchOpen = !this.state.isSearchOpen;
    },

    async onClickUnfollow() {
        const thread = this.state.thread;
        await thread.selfFollower.remove();
        this.onFollowerChanged(thread);
    },

    onCloseFullComposerCallback() {
        this.toggleComposer();
        super.onCloseFullComposerCallback();
    },

    onFollowerChanged(thread) {
        document.body.click(); // hack to close dropdown
        this.reloadParentView();
        this.load(thread, ["followers", "suggestedRecipients"]);
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
        if (this.props.webRecord) {
            await this.props.webRecord.load();
        }
    },

    async scheduleActivity() {
        this.closeSearch();
        const schedule = async (thread) => {
            await this.store.scheduleActivity(thread.model, [thread.id]);
            this.load(thread, ["activities", "messages"]);
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

    toggleComposer(mode = false) {
        this.closeSearch();
        const toggle = () => {
            if (this.state.composerType === mode) {
                this.state.composerType = false;
            } else {
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
