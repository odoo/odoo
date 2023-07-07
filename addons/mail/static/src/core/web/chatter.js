/* @odoo-module */

import { AttachmentList } from "@mail/core/common/attachment_list";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { Composer } from "@mail/core/common/composer";
import { useDropzone } from "@mail/core/common/dropzone_hook";
import { useMessaging, useStore } from "@mail/core/common/messaging_hook";
import { Thread } from "@mail/core/common/thread";
import { Activity } from "@mail/core/web/activity";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";
import { SuggestedRecipientsList } from "@mail/core/web/suggested_recipient_list";
import { useHover, useScrollPosition } from "@mail/utils/common/hooks";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";

import {
    Component,
    markup,
    onMounted,
    onPatched,
    onWillStart,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { FileUploader } from "@web/views/fields/file_handler";
import { RecipientList } from "./recipient_list";

/**
 * @typedef {Object} Props
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class Chatter extends Component {
    static template = "mail.Chatter";
    static components = {
        AttachmentList,
        Dropdown,
        Thread,
        Composer,
        Activity,
        FileUploader,
        SuggestedRecipientsList,
    };
    static props = [
        "close?",
        "compactHeight?",
        "displayName?",
        "hasActivities?",
        "hasFollowers?",
        "hasMessageList?",
        "hasMessageListScrollAdjust?",
        "hasParentReloadOnAttachmentsChanged?",
        "hasParentReloadOnFollowersUpdate?",
        "hasParentReloadOnMessagePosted?",
        "isAttachmentBoxVisibleInitially?",
        "isInFormSheetBg?",
        "threadId?",
        "threadModel",
        "webRecord?",
        "saveRecord?",
    ];
    static defaultProps = {
        compactHeight: false,
        hasActivities: true,
        hasFollowers: true,
        hasMessageList: true,
        hasMessageListScrollAdjust: false,
        hasParentReloadOnAttachmentsChanged: false,
        hasParentReloadOnFollowersUpdate: false,
        hasParentReloadOnMessagePosted: false,
        isAttachmentBoxVisibleInitially: false,
        isInFormSheetBg: true,
        threadId: false,
    };

    setup() {
        this.action = useService("action");
        this.attachmentBox = useRef("attachment-box");
        this.messaging = useMessaging();
        /** @type {import("@mail/activity/activity_service").ActivityService} */
        this.activityService = useState(useService("mail.activity"));
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = useService("mail.thread");
        this.store = useStore();
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.state = useState({
            isAttachmentBoxOpened: this.props.isAttachmentBoxVisibleInitially,
            jumpThreadPresent: 0,
            showActivities: true,
            /** @type {import("@mail/core/common/thread_model").Thread} */
            thread: undefined,
        });
        this.unfollowHover = useHover("unfollow");
        this.attachmentUploader = useAttachmentUploader(
            this.threadService.getThread(this.props.threadModel, this.props.threadId)
        );
        this.scrollPosition = useScrollPosition("root", undefined, "top");
        this.rootRef = useRef("root");
        this.onScrollDebounced = useThrottleForAnimation(this.onScroll);
        this.recipientsPopover = usePopover(RecipientList);
        useChildSubEnv({ inChatter: true });
        useDropzone(
            this.rootRef,
            async (ev) => {
                if (this.state.thread.composer.type) {
                    return;
                }
                if (isDragSourceExternalFile(ev.dataTransfer)) {
                    const files = [...ev.dataTransfer.files];
                    if (!this.props.threadId) {
                        const saved = await this.props.saveRecord?.();
                        if (!saved) {
                            return;
                        }
                    }
                    files.forEach(this.attachmentUploader.uploadFile);
                    this.state.isAttachmentBoxOpened = true;
                }
            },
            "o-mail-Chatter-dropzone"
        );

        onMounted(this.scrollPosition.restore);
        onPatched(this.scrollPosition.restore);
        onWillStart(() => {
            if (this.props.threadId) {
                this.state.thread = this.threadService.insert({
                    id: this.props.threadId,
                    model: this.props.threadModel,
                    name: this.props.webRecord?.data?.display_name || undefined,
                });
            }
            return this.load(this.props.threadId, [
                "followers",
                "attachments",
                "suggestedRecipients",
            ]);
        });
        onWillUpdateProps((nextProps) => {
            this.load(nextProps.threadId, ["followers", "attachments", "suggestedRecipients"]);
            if (nextProps.threadId === false) {
                this.state.thread.composer.type = false;
            }
            this.attachmentUploader.thread = this.threadService.getThread(
                nextProps.threadModel,
                nextProps.threadId
            );
            if (this.onNextUpdate) {
                if (!this.onNextUpdate(nextProps)) {
                    this.onNextUpdate = null;
                }
            }
        });
        useEffect(
            (opened) => {
                if (opened) {
                    this.attachmentBox.el.scrollIntoView({ block: "center" });
                }
            },
            () => [this.state.isAttachmentBoxOpened]
        );
    }

    /**
     * @returns {import("@mail/core/web/activity_model").Activity[]}
     */
    get activities() {
        return this.state.thread.activities;
    }

    get followerButtonLabel() {
        return _t("Show Followers");
    }

    get followingText() {
        return _t("Following");
    }

    /**
     * @returns {boolean}
     */
    get isDisabled() {
        return !this.props.threadId || !this.state.thread.hasReadAccess;
    }

    get attachments() {
        return this.state.thread?.attachments ?? [];
    }

    /**
     * @returns {string}
     */
    get toRecipientsText() {
        const followers = [...this.state.thread.followers].slice(0, 5).map(({ partner }) => {
            if (partner === this.store.self) {
                return `<span class="text-muted" title="${escape(partner.email)}">me</span>`;
            }
            return `<span class="text-muted" title="${escape(partner.email)}">${escape(
                partner.emailWithoutDomain
            )}</span>`;
        });
        const formatter = new Intl.ListFormat(
            this.store.env.services["user"].lang?.replace("_", "-"),
            { type: "unit" }
        );
        if (this.state.thread.followers.size > 5) {
            followers.push("…");
        }
        return markup(formatter.format(followers));
    }

    /**
     * @param {number} threadId
     * @param {['activities'|'followers'|'attachments'|'messages'|'suggestedRecipients']} requestList
     */
    load(
        threadId = this.props.threadId,
        requestList = ["followers", "attachments", "messages", "suggestedRecipients"]
    ) {
        const { threadModel } = this.props;
        this.state.thread = this.threadService.getThread(threadModel, threadId);
        this.scrollPosition.model = this.state.thread.scrollPosition;
        if (!threadId) {
            return;
        }
        if (this.props.hasActivities && !requestList.includes("activities")) {
            requestList.push("activities");
        }
        this.threadService.fetchData(this.state.thread, requestList);
    }

    onClickAddFollowers() {
        document.body.click(); // hack to close dropdown
        const action = {
            type: "ir.actions.act_window",
            res_model: "mail.wizard.invite",
            view_mode: "form",
            views: [[false, "form"]],
            name: _t("Invite Follower"),
            target: "new",
            context: {
                default_res_model: this.props.threadModel,
                default_res_id: this.props.threadId,
            },
        };
        this.env.services.action.doAction(action, {
            onClose: () => {
                this.load(this.props.threadId, ["followers", "suggestedRecipients"]);
                if (this.props.hasParentReloadOnFollowersUpdate) {
                    this.reloadParentView();
                }
            },
        });
    }

    onClickDetails(ev, follower) {
        this.messaging.openDocument({ id: follower.partner.id, model: "res.partner" });
        document.body.click(); // hack to close dropdown
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("@mail/core/common/follower_model").Follower} follower
     */
    async onClickEdit(ev, follower) {
        this.env.services.dialog.add(FollowerSubtypeDialog, {
            follower,
            onFollowerChanged: () => this.onFollowerChanged(),
        });
        document.body.click(); // hack to close dropdown
    }

    async _follow(threadModel, threadId) {
        await this.orm.call(threadModel, "message_subscribe", [[threadId]], {
            partner_ids: [this.store.self.id],
        });
        this.onFollowerChanged();
    }

    async onClickFollow() {
        if (this.props.threadId) {
            this._follow(this.props.threadModel, this.props.threadId);
        } else {
            this.onNextUpdate = (nextProps) => {
                if (nextProps.threadId) {
                    this._follow(nextProps.threadModel, nextProps.threadId);
                } else {
                    return true;
                }
            };
            await this.props.saveRecord?.();
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("@mail/core/common/follower_model").Follower} follower
     */
    async onClickRemove(ev, follower) {
        await this.threadService.removeFollower(follower);
        this.onFollowerChanged();
        document.body.click(); // hack to close dropdown
    }

    async onClickUnfollow() {
        await this.threadService.removeFollower(this.state.thread.followerOfSelf);
        this.onFollowerChanged();
    }

    onFollowerChanged() {
        this.reloadParentView();
        this.load(this.props.threadId, ["followers", "suggestedRecipients"]);
    }

    onPostCallback() {
        if (this.props.hasParentReloadOnMessagePosted) {
            this.reloadParentView();
        }
        this.toggleComposer();
        this.state.jumpThreadPresent++;
        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
        this.load(this.props.threadId, ["followers", "messages", "suggestedRecipients"]);
    }

    async reloadParentView() {
        await this.props.saveRecord?.();
        if (this.props.webRecord) {
            await this.props.webRecord.model.root.load(
                { resId: this.props.threadId },
                { keepChanges: true }
            );
            this.props.webRecord.model.notify();
        }
    }

    toggleComposer(mode = false) {
        const toggle = () => {
            if (this.state.thread.composer.type === mode) {
                this.state.thread.composer.type = false;
            } else {
                this.state.thread.composer.type = mode;
            }
        };
        if (this.props.threadId) {
            toggle();
        } else {
            this.onNextUpdate = (nextProps) => {
                // @returns {boolean} retry on next update
                // if there is no threadId, the save operation probably failed
                // probably because some required field is not set
                if (nextProps.threadId) {
                    toggle();
                } else {
                    return true;
                }
            };
            this.props.saveRecord?.();
        }
    }

    toggleActivities() {
        this.state.showActivities = !this.state.showActivities;
    }

    async scheduleActivity() {
        const schedule = async (threadId) => {
            await this.activityService.schedule(this.props.threadModel, threadId);
            this.load(this.props.threadId, ["activities", "messages"]);
        };
        if (this.props.threadId) {
            schedule(this.props.threadId);
        } else {
            this.onNextUpdate = (nextProps) => {
                if (nextProps.threadId) {
                    schedule(nextProps.threadId);
                } else {
                    return true;
                }
            };
            this.props.saveRecord?.();
        }
    }

    get unfollowText() {
        return _t("Unfollow");
    }

    async unlinkAttachment(attachment) {
        await this.attachmentUploader.unlink(attachment);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
    }

    onUploaded(data) {
        this.attachmentUploader.uploadData(data);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
        this.state.isAttachmentBoxOpened = true;
        this.scrollPosition.ref.el.scrollTop = 0;
    }

    onClickAddAttachments() {
        if (this.attachments.length === 0) {
            return;
        }
        this.state.isAttachmentBoxOpened = !this.state.isAttachmentBoxOpened;
    }

    async onClickAttachFile(ev) {
        if (this.props.threadId) {
            return;
        }
        const saved = await this.props.saveRecord?.();
        if (!saved) {
            return false;
        }
    }

    onScroll() {
        this.state.isTopStickyPinned = this.rootRef.el.scrollTop !== 0;
    }

    onClickRecipientList(ev) {
        if (this.recipientsPopover.isOpen) {
            return this.recipientsPopover.close();
        }
        this.recipientsPopover.open(ev.target, { thread: this.state.thread });
    }
}
