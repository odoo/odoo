import { Chatter } from "@mail/chatter/web_portal/chatter";
import { Activity } from "@mail/core/web/activity";
import { SuggestedRecipientsList } from "@mail/core/web/suggested_recipient_list";
import { RecipientList } from "@mail/core/web/recipient_list";
import { FollowerList } from "@mail/core/web/follower_list";
import { useHover } from "@mail/utils/common/hooks";
import { useDropzone } from "@mail/core/common/dropzone_hook";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";

import { useState, markup, useEffect } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { escape } from "@web/core/utils/strings";
import { formatList } from "@web/core/l10n/utils";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export const DELAY_FOR_SPINNER = 1000;

Object.assign(Chatter.components, {
    Activity,
    SuggestedRecipientsList,
    FollowerList,
});

Chatter.props.push(
    "close?",
    "compactHeight?",
    "has_activities?",
    "hasParentReloadOnAttachmentsChanged?",
    "hasParentReloadOnFollowersUpdate?",
    "hasParentReloadOnMessagePosted?",
    "isAttachmentBoxVisibleInitially?",
    "isChatterAside?",
    "isInFormSheetBg?"
);

Object.assign(Chatter.defaultProps, {
    compactHeight: false,
    has_activities: true,
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
        super.setup(...arguments);
        this.activityService = useState(useService("mail.activity"));
        this.recipientsPopover = usePopover(RecipientList);
        Object.assign(this.state, {
            isAttachmentBoxOpened: this.props.isAttachmentBoxVisibleInitially,
            showActivities: true,
            showAttachmentLoading: false,
        });
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
    },

    /**
     * @returns {import("models").Activity[]}
     */
    get activities() {
        return this.state.thread?.activities ?? [];
    },

    get afterPostRequestList() {
        return [...super.afterPostRequestList, "followers", "suggestedRecipients"];
    },

    get attachments() {
        return this.state.thread?.attachments ?? [];
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

    get requestList() {
        return [...super.requestList, "followers", "attachments", "suggestedRecipients"];
    },

    /**
     * @returns {string}
     */
    get toRecipientsText() {
        if (this.state.thread?.recipients.length === 0) {
            return _t("No recipient");
        }
        const recipients = [...(this.state.thread?.recipients ?? [])]
            .slice(0, 5)
            .map(({ partner }) => {
                const text = partner.email ? partner.emailWithoutDomain : partner.name;
                return `<span class="text-muted" title="${escape(
                    partner.email || _t("no email address")
                )}">${escape(text)}</span>`;
            });
        if (this.state.thread && this.state.thread.recipients.length > 5) {
            recipients.push(
                escape(
                    _t("%(recipientCount)s more", {
                        recipientCount: this.state.thread.recipients.length - 5,
                    })
                )
            );
        }
        return markup(formatList(recipients));
    },

    get unfollowText() {
        return _t("Unfollow");
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
            this.state.thread.scrollTop = 0;
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

    onClickRecipientList(ev) {
        if (this.recipientsPopover.isOpen) {
            return this.recipientsPopover.close();
        }
        this.recipientsPopover.open(ev.target, { thread: this.state.thread });
    },

    async onClickUnfollow() {
        const thread = this.state.thread;
        await thread.selfFollower.remove();
        this.onFollowerChanged(thread);
    },

    onFollowerChanged(thread) {
        document.body.click(); // hack to close dropdown
        this.reloadParentView();
        this.load(thread, ["followers", "suggestedRecipients"]);
    },

    onPostCallback() {
        if (this.props.hasParentReloadOnMessagePosted) {
            this.reloadParentView();
        }
        this.toggleComposer();
        super.onPostCallback();
    },

    onSuggestedRecipientAdded(thread) {
        this.load(thread, ["suggestedRecipients"]);
    },

    onUploaded(data) {
        this.attachmentUploader.uploadData(data);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
        this.state.isAttachmentBoxOpened = true;
        this.rootRef.el.scrollTop = 0;
        this.state.thread.scrollTop = 0;
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
            await this.activityService.schedule(thread.model, [thread.id]);
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

    async unlinkAttachment(attachment) {
        await super.unlinkAttachment(attachment);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
    },
});
